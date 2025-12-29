import cv2
import time
import threading
import numpy as np
import mediapipe as mp
from deepface import DeepFace
import logging
import os

from src.events.bus import bus
from src.vision.camera_manager import CameraManager
from src.performance_monitor import performance_monitor
from src.vision.privacy_manager import privacy_manager

logger = logging.getLogger(__name__)


class Observer(threading.Thread):
    def __init__(self, frame_rate=1, advisory_mode=None):
        super().__init__()
        self.name = "VisionObserverThread"
        self.daemon = True
        self.running = threading.Event()
        self.frame_interval = 1.0 / frame_rate

        # Advisory mode configuration - makes observer signals advisory by default
        # Read from environment, default to True for production safety
        if advisory_mode is None:
            self.advisory_mode = (
                os.getenv("OBSERVER_ADVISORY_MODE", "true").lower() == "true"
            )
        else:
            self.advisory_mode = advisory_mode

        # State Tracking
        self.user_present = False
        self.last_posture = None
        self.last_emotion = None
        self.cam = None  # Camera instance for active observation

        # Enhanced emotion tracking with multi-frame averaging
        self.emotion_history = []
        self.emotion_history_size = 5  # Average over last 5 frames
        self.emotion_stability_threshold = (
            0.7  # Confidence threshold for stable detection
        )

        # Nutrition tracking
        self.nutrition_mode = False
        self.last_meal_analysis = None

        # MediaPipe Initialization
        self.mp_pose = mp.solutions.pose
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_hands = mp.solutions.hands  # Added for gesture recognition
        self.pose = self.mp_pose.Pose()
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=0, min_detection_confidence=0.5
        )
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # Initialize Episodic Memory for event logging
        self._init_memory_system()

        # DeepFace Model Warm-up
        logger.info("Warming up DeepFace model...")
        try:
            dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
            DeepFace.analyze(
                dummy_frame, actions=["emotion"], enforce_detection=False, silent=True
            )
            logger.info("DeepFace model ready.")
        except Exception as e:
            logger.error(f"Failed to initialize DeepFace: {e}")

        # Initialize object detection
        self._init_object_detection()

    def _init_memory_system(self):
        """Initialize Episodic Memory for event logging"""
        try:
            from src.memory.episodic_memory import EpisodicMemory
            self.episodic_memory = EpisodicMemory()
            logger.info("Episodic memory initialized for vision observer")
        except Exception as e:
            logger.error(f"Failed to initialize episodic memory: {e}")
            self.episodic_memory = None
    
    def _init_object_detection(self):
        """Initialize OpenCV DNN object detection model"""
        try:
            # Load YOLOv3-tiny model for object detection
            self.net = cv2.dnn.readNetFromDarknet(
                "yolov3-tiny.cfg", "yolov3-tiny.weights"
            )
            # Try to use CUDA if available
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
        except:
            logger.warning("YOLO model files not found, object detection disabled")
            self.net = None

        # COCO class names
        self.classes = []
        try:
            with open("coco.names", "r") as f:
                self.classes = [line.strip() for line in f.readlines()]
        except:
            logger.warning("COCO class names file not found")
            self.classes = [
                "person",
                "bicycle",
                "car",
                "motorcycle",
                "airplane",
                "bus",
                "train",
                "truck",
                "boat",
                "traffic light",
                "fire hydrant",
                "stop sign",
                "parking meter",
                "bench",
                "bird",
                "cat",
                "dog",
            ]

    def _analyze_presence(self, pose_landmarks) -> bool:
        return pose_landmarks is not None

    def _analyze_posture(self, pose_landmarks, frame_shape) -> str:
        if not pose_landmarks:
            return "UNKNOWN"
        try:
            landmarks = pose_landmarks.landmark
            h, w, _ = frame_shape

            nose = landmarks[self.mp_pose.PoseLandmark.NOSE.value]
            left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
            right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]

            if not (
                nose.visibility > 0.6
                and left_shoulder.visibility > 0.6
                and right_shoulder.visibility > 0.6
            ):
                return "UNKNOWN"

            shoulder_y = (left_shoulder.y + right_shoulder.y) / 2

            if nose.y > shoulder_y + 0.05:
                return "SLOUCHING"
            else:
                return "UPRIGHT"
        except Exception:
            return "UNKNOWN"

    def _analyze_emotion(self, frame) -> tuple[str, float]:
        """Analyze emotion with confidence scoring, multi-frame averaging, and performance monitoring"""
        emotion_timer = performance_monitor.start_timer("emotion_analysis")

        try:
            # First use MediaPipe for face detection with confidence
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_results = self.face_detection.process(image_rgb)

            if not face_results.detections:
                performance_monitor.end_timer(emotion_timer, "emotion_analysis")
                return "UNKNOWN", 0.0

            # Get the most confident face detection
            best_detection = max(face_results.detections, key=lambda d: d.score[0])
            face_confidence = float(best_detection.score[0])

            # Only proceed if face detection confidence is high enough
            if face_confidence < 0.7:
                performance_monitor.end_timer(emotion_timer, "emotion_analysis")
                return "UNKNOWN", face_confidence

            # Use DeepFace for emotion analysis
            analysis = DeepFace.analyze(
                img_path=frame,
                actions=["emotion"],
                enforce_detection=False,  # Already validated by MediaPipe
                detector_backend="retinaface",
            )

            emotion = analysis[0]["dominant_emotion"].upper()
            emotion_confidence = float(analysis[0]["emotion"][emotion.lower()])

            # Combine face detection and emotion confidence
            combined_confidence = min(face_confidence, emotion_confidence / 100.0)

            # Add to emotion history for stability analysis
            self.emotion_history.append((emotion, combined_confidence))
            if len(self.emotion_history) > self.emotion_history_size:
                self.emotion_history.pop(0)

            # Calculate stable emotion using majority voting with confidence weighting
            if len(self.emotion_history) >= 3:
                stable_emotion, stable_confidence = self._calculate_stable_emotion()
                latency = performance_monitor.end_timer(
                    emotion_timer, "emotion_analysis"
                )
                logger.debug(f"Emotion analysis completed in {latency:.0f}ms")
                return stable_emotion, stable_confidence

            latency = performance_monitor.end_timer(emotion_timer, "emotion_analysis")
            logger.debug(f"Emotion analysis completed in {latency:.0f}ms")
            return emotion, combined_confidence

        except Exception as e:
            logger.debug(f"Emotion analysis failed: {e}")
            performance_monitor.end_timer(emotion_timer, "emotion_analysis")
            return "UNKNOWN", 0.0

    def _calculate_stable_emotion(self) -> tuple[str, float]:
        """Calculate stable emotion from recent history using weighted voting"""
        if not self.emotion_history:
            return "UNKNOWN", 0.0

        # Group by emotion and calculate weighted confidence
        emotion_weights = {}
        total_weight = 0

        for emotion, confidence in self.emotion_history:
            weight = confidence**2  # Square confidence for stronger weighting
            emotion_weights[emotion] = emotion_weights.get(emotion, 0) + weight
            total_weight += weight

        if total_weight == 0:
            return "UNKNOWN", 0.0

        # Find emotion with highest weighted confidence
        stable_emotion = max(emotion_weights.items(), key=lambda x: x[1])[0]

        # Calculate stability confidence (how dominant this emotion is)
        stable_weight = emotion_weights[stable_emotion]
        stability_confidence = stable_weight / total_weight

        # Only return stable emotion if it meets threshold
        if stability_confidence >= self.emotion_stability_threshold:
            return stable_emotion, stability_confidence

        return "UNKNOWN", stability_confidence

    def _get_emotion_recommendation(self, emotion: str, confidence: float) -> str:
        """Generate advisory recommendation based on detected emotion"""
        emotion_lower = emotion.lower()

        recommendations = {
            "sad": "consider_empathy_response",
            "angry": "consider_deescalation_support",
            "fear": "consider_reassurance",
            "happy": "acknowledge_positive_state",
            "surprise": "consider_engagement",
            "disgust": "consider_boundary_setting",
            "neutral": "maintain_current_interaction",
        }

        base_recommendation = recommendations.get(
            emotion_lower, "monitor_emotional_state"
        )

        # Add confidence modifier
        if confidence > 0.8:
            return f"{base_recommendation}_high_confidence"
        elif confidence > 0.6:
            return f"{base_recommendation}_moderate_confidence"
        else:
            return f"{base_recommendation}_low_confidence"
    
    def _analyze_gestures(self, frame) -> tuple[str, float]:
        """Analyze hand gestures using MediaPipe Hands"""
        gesture_timer = performance_monitor.start_timer("gesture_analysis")
        
        try:
            # Check privacy consent for gesture detection
            if not privacy_manager.is_vision_allowed("gesture_detection"):
                performance_monitor.end_timer(gesture_timer, "gesture_analysis")
                return "UNKNOWN", 0.0
                
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            hand_results = self.hands.process(image_rgb)
            
            if not hand_results.multi_hand_landmarks:
                performance_monitor.end_timer(gesture_timer, "gesture_analysis")
                return "UNKNOWN", 0.0
                
            # Simple gesture classification based on hand landmarks
            # This is a basic implementation - can be enhanced with ML models
            gestures = []
            confidences = []
            
            for hand_landmarks in hand_results.multi_hand_landmarks:
                # Get thumb and index finger positions
                thumb_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
                index_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FIP]
                middle_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_TIP]
                
                # Calculate distance between thumb and index finger
                thumb_index_dist = ((thumb_tip.x - index_tip.x)**2 + 
                                  (thumb_tip.y - index_tip.y)**2)**0.5
                
                # Simple gesture detection
                if thumb_index_dist < 0.05:  # Thumb and index close together
                    gestures.append("PINCH")
                    confidences.append(0.8)
                elif thumb_tip.y < index_tip.y and thumb_tip.y < middle_tip.y:
                    gestures.append("THUMBS_UP")
                    confidences.append(0.7)
                else:
                    gestures.append("OPEN_HAND")
                    confidences.append(0.6)
            
            # Return the most confident gesture
            if gestures:
                max_conf_idx = confidences.index(max(confidences))
                gesture_latency = performance_monitor.end_timer(
                    gesture_timer, "gesture_analysis"
                )
                logger.debug(f"Gesture analysis completed in {gesture_latency:.0f}ms")
                return gestures[max_conf_idx], max(confidences)
            
        except Exception as e:
            logger.debug(f"Gesture analysis failed: {e}")
            
        performance_monitor.end_timer(gesture_timer, "gesture_analysis")
        return "UNKNOWN", 0.0
    
    def _get_gesture_recommendation(self, gesture: str, confidence: float) -> str:
        """Generate advisory recommendation based on detected gesture"""
        gesture_lower = gesture.lower()
        
        recommendations = {
            "pinch": "consider_zoom_interaction",
            "thumbs_up": "consider_positive_feedback",
            "open_hand": "consider_greeting_response",
            "wave": "consider_attention_request",
            "point": "consider_direction_indication",
        }
        
        base_recommendation = recommendations.get(
            gesture_lower, "monitor_gesture"
        )
        
        # Add confidence modifier
        if confidence > 0.8:
            return f"{base_recommendation}_high_confidence"
        elif confidence > 0.6:
            return f"{base_recommendation}_moderate_confidence"
        else:
            return f"{base_recommendation}_low_confidence"
    
    def _log_gesture_event(self, gesture: str, confidence: float):
        """Log gesture event to episodic memory"""
        if self.episodic_memory is not None:
            try:
                event_data = {
                    "gesture": gesture,
                    "confidence": confidence,
                    "source": "vision_observer",
                    "feature": "gesture_detection"
                }
                self.episodic_memory.store_event(
                    event_type="vision_gesture",
                    data=event_data,
                    metadata={"agent": "agent_env", "type": "gesture"}
                )
                logger.debug(f"Logged gesture event to episodic memory: {gesture}")
            except Exception as e:
                logger.error(f"Failed to log gesture event: {e}")

    def run(self):
        self.running.set()
        logger.info("Vision Observer thread started.")
        bus.publish("OBSERVER_STATE_CHANGED", {"active": True})

        # Use configured camera URL from environment
        camera_url = os.getenv("CAMERA_URL", "rtsp://127.0.0.1:8554/webcam")
        logger.info(f"Observer using camera: {camera_url}")
        with CameraManager(camera_url) as cam:
            self.cam = cam  # Store camera instance for active observation
            if not cam:
                logger.error("Observer failed to acquire camera, thread stopping.")
                bus.publish("OBSERVER_STATE_CHANGED", {"active": False})
                self.running.clear()
                return

            while self.running.is_set():
                observer_timer = performance_monitor.start_timer("observer_processing")
                start_time = time.time()

                success, frame = cam.get_frame()
                if not success:
                    logger.warning("Failed to grab frame from camera.")
                    performance_monitor.end_timer(observer_timer, "observer_processing")
                    time.sleep(self.frame_interval)
                    continue

                image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pose_results = self.pose.process(image_rgb)

                is_present = self._analyze_presence(pose_results.pose_landmarks)
                current_posture = self._analyze_posture(
                    pose_results.pose_landmarks, frame.shape
                )
                current_emotion, emotion_confidence = (
                    self._analyze_emotion(frame) if is_present else ("UNKNOWN", 0.0)
                )
                current_gesture, gesture_confidence = (
                    self._analyze_gestures(frame) if is_present else ("UNKNOWN", 0.0)
                )

                # Record observer frame rate
                performance_monitor.record_metric(
                    "observer_frames_per_second", 1.0 / self.frame_interval
                )

                if is_present != self.user_present:
                    self.user_present = is_present
                    event_type = (
                        "vision.user.arrived" if is_present else "vision.user.left"
                    )
                    bus.publish(event_type, {"timestamp": time.time()})
                    logger.info(f"EVENT: {event_type}")

                if (
                    is_present
                    and current_posture == "SLOUCHING"
                    and self.last_posture != "SLOUCHING"
                ):
                    if self.advisory_mode:
                        # Advisory mode: publish observation for agents to decide action
                        bus.publish(
                            "vision.observation.posture",
                            {
                                "posture": "SLOUCHING",
                                "recommendation": "consider_posture_intervention",
                                "confidence": 0.8,
                                "timestamp": time.time(),
                            },
                        )
                        logger.info("ADVISORY: vision.observation.posture (SLOUCHING)")
                    else:
                        # Legacy direct action mode
                        bus.publish("vision.posture.bad", {"posture": "SLOUCHING"})
                        logger.info("EVENT: vision.posture.bad")

                if (
                    is_present
                    and current_emotion != self.last_emotion
                    and current_emotion != "UNKNOWN"
                    and emotion_confidence > 0.6  # Confidence threshold
                ):
                    if self.advisory_mode:
                        # Advisory mode: publish observation with recommendation
                        recommendation = self._get_emotion_recommendation(
                            current_emotion, emotion_confidence
                        )
                        bus.publish(
                            "vision.observation.emotion",
                            {
                                "emotion": current_emotion,
                                "confidence": emotion_confidence,
                                "recommendation": recommendation,
                                "timestamp": time.time(),
                            },
                        )
                        logger.info(
                            f"ADVISORY: vision.observation.emotion ({current_emotion}, {emotion_confidence:.2f})"
                        )
                    else:
                        # Legacy direct action mode
                        bus.publish(
                            "vision.emotion.detected",
                            {
                                "emotion": current_emotion,
                                "confidence": emotion_confidence,
                                "timestamp": time.time(),
                            },
                        )
                        logger.info(
                            f"EVENT: vision.emotion.detected ({current_emotion}, {emotion_confidence:.2f})"
                        )

                self.last_posture = current_posture
                self.last_emotion = current_emotion
                
                # Gesture detection and event publishing
                if (
                    is_present
                    and current_gesture != "UNKNOWN"
                    and gesture_confidence > 0.6  # Confidence threshold
                ):
                    if self.advisory_mode:
                        # Advisory mode: publish observation with recommendation
                        recommendation = self._get_gesture_recommendation(
                            current_gesture, gesture_confidence
                        )
                        bus.publish(
                            "vision.observation.gesture",
                            {
                                "gesture": current_gesture,
                                "confidence": gesture_confidence,
                                "recommendation": recommendation,
                                "timestamp": time.time(),
                            },
                        )
                        logger.info(
                            f"ADVISORY: vision.observation.gesture ({current_gesture}, {gesture_confidence:.2f})"
                        )
                        
                        # Log gesture event to episodic memory
                        self._log_gesture_event(current_gesture, gesture_confidence)
                    else:
                        # Legacy direct action mode
                        bus.publish(
                            "vision.gesture.detected",
                            {
                                "gesture": current_gesture,
                                "confidence": gesture_confidence,
                                "timestamp": time.time(),
                            },
                        )
                        logger.info(
                            f"EVENT: vision.gesture.detected ({current_gesture}, {gesture_confidence:.2f})"
                        )
                
                # End observer processing timer
                observer_latency = performance_monitor.end_timer(
                    observer_timer, "observer_processing"
                )

                elapsed = time.time() - start_time
                sleep_time = self.frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        self.pose.close()
        self.face_detection.close()
        logger.info("Vision Observer thread stopped.")
        bus.publish("OBSERVER_STATE_CHANGED", {"active": False})

    def trigger_active_observation(self, analysis_type="full"):
        """Trigger detailed analysis of current scene"""
        try:
            # Get current frame
            if self.cam is None:
                return {"error": "Camera not available"}

            success, frame = self.cam.get_frame()
            if not success:
                logger.warning("Failed to get frame for active observation")
                return {"error": "Failed to capture frame"}

            results = {}

            if analysis_type in ["full", "objects"]:
                # Object detection
                objects = self._detect_objects(frame)
                results["objects"] = objects

            if analysis_type in ["full", "detailed"]:
                # Detailed emotion and pose analysis
                image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pose_results = self.pose.process(image_rgb)

                emotion, confidence = self._analyze_emotion(frame)
                posture = self._analyze_posture(
                    pose_results.pose_landmarks, frame.shape
                )

                results.update(
                    {
                        "emotion": emotion,
                        "emotion_confidence": confidence,
                        "posture": posture,
                        "user_present": self._analyze_presence(
                            pose_results.pose_landmarks
                        ),
                    }
                )

            if analysis_type in ["full", "nutrition"] or self.nutrition_mode:
                # Nutrition-focused analysis
                nutrition_analysis = self._analyze_nutrition_scene(frame)
                results["nutrition"] = nutrition_analysis
                self.last_meal_analysis = nutrition_analysis

            # Emit event with detailed analysis
            bus.publish(
                "vision.active_analysis",
                {
                    "analysis_type": analysis_type,
                    "results": results,
                    "timestamp": time.time(),
                },
            )

            logger.info(f"Active observation completed: {analysis_type}")
            return results

        except Exception as e:
            logger.error(f"Active observation failed: {e}")
            return {"error": str(e)}

    def _analyze_nutrition_scene(self, frame) -> dict:
        """Analyze scene for nutrition tracking"""
        try:
            # Detect food-related objects
            objects = self._detect_objects(frame)
            food_objects = [
                obj
                for obj in objects
                if obj["class"]
                in [
                    "apple",
                    "banana",
                    "orange",
                    "bowl",
                    "cup",
                    "bottle",
                    "plate",
                    "fork",
                    "spoon",
                ]
                and obj["confidence"] > 0.6
            ]

            # Estimate meal type based on detected objects
            meal_type = self._classify_meal(food_objects)

            # Estimate portion sizes (basic heuristic)
            portion_estimate = len(food_objects) * 0.3  # Rough estimate

            return {
                "detected_foods": food_objects,
                "meal_type": meal_type,
                "estimated_portion": portion_estimate,
                "timestamp": time.time(),
            }

        except Exception as e:
            logger.error(f"Nutrition analysis failed: {e}")
            return {"error": str(e)}

    def _classify_meal(self, food_objects) -> str:
        """Classify meal type based on detected objects"""
        if not food_objects:
            return "unknown"

        # Simple classification based on common meal patterns
        has_drink = any(obj["class"] in ["cup", "bottle"] for obj in food_objects)
        has_plate = any(obj["class"] == "plate" for obj in food_objects)
        has_fruits = any(
            obj["class"] in ["apple", "banana", "orange"] for obj in food_objects
        )

        if has_plate and has_drink:
            return "meal"
        elif has_fruits and not has_plate:
            return "snack"
        elif has_drink and not has_plate:
            return "beverage"
        else:
            return "mixed"

    def set_nutrition_mode(self, enabled: bool):
        """Enable/disable nutrition tracking mode"""
        self.nutrition_mode = enabled
        logger.info(f"Nutrition tracking mode: {'enabled' if enabled else 'disabled'}")

    def set_advisory_mode(self, enabled: bool):
        """Enable/disable advisory mode for observer signals"""
        self.advisory_mode = enabled
        logger.info(f"Observer advisory mode: {'enabled' if enabled else 'disabled'}")
        # Publish mode change event
        bus.publish(
            "vision.observer.mode_changed",
            {"advisory_mode": enabled, "timestamp": time.time()},
        )

    def _detect_objects(self, frame) -> list:
        """Detect objects in frame using YOLO"""
        if self.net is None:
            return []

        try:
            height, width = frame.shape[:2]

            # Create blob from image
            blob = cv2.dnn.blobFromImage(
                frame, 1 / 255.0, (416, 416), swapRB=True, crop=False
            )
            self.net.setInput(blob)

            # Get output layer names
            layer_names = self.net.getLayerNames()
            output_layers = [
                layer_names[i - 1] for i in self.net.getUnconnectedOutLayers()
            ]

            # Forward pass
            outputs = self.net.forward(output_layers)

            # Process detections
            detections = []
            for output in outputs:
                for detection in output:
                    scores = detection[5:]
                    class_id = int(np.argmax(scores))
                    confidence = float(scores[class_id])

                    if confidence > 0.5:  # Confidence threshold
                        center_x = int(float(detection[0]) * width)
                        center_y = int(float(detection[1]) * height)
                        w = int(float(detection[2]) * width)
                        h = int(float(detection[3]) * height)

                        x = int(center_x - w / 2)
                        y = int(center_y - h / 2)

                        detections.append(
                            {
                                "class": self.classes[class_id]
                                if class_id < len(self.classes)
                                else "unknown",
                                "confidence": float(confidence),
                                "bbox": [x, y, w, h],
                            }
                        )

            return detections

        except Exception as e:
            logger.error(f"Object detection failed: {e}")
            return []

    def stop(self):
        self.running.clear()
        # Clean up MediaPipe resources
        self.hands.close()
