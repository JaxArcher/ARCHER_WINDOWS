"""
Multimodal AI Agent for ARCHER

Advanced vision-language understanding capabilities using CLIP and BLIP models.
"""

import torch
import logging
from PIL import Image
import numpy as np
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MultimodalAgent:
    """
    Multimodal AI agent for vision-language understanding.
    
    Capabilities:
    - Image-text similarity scoring using CLIP
    - Visual question answering using BLIP
    - Scene understanding with language context
    - Cross-modal retrieval and analysis
    - Image captioning and description
    """
    
    def __init__(self, device: str = "cuda" if torch.cuda.is_available() else "cpu"):
        self.device = device
        self.clip_model, self.preprocess = self._load_clip_model()
        self.blip_model = self._load_blip_model()
        self.cache = {}
        self.initialized = True
        
        logger.info(f"MultimodalAgent initialized on {device}")
        if self.clip_model:
            logger.info("CLIP model loaded successfully")
        if self.blip_model:
            logger.info("BLIP model loaded successfully")
        
    def _load_clip_model(self) -> tuple:
        """Load CLIP model for vision-language understanding."""
        try:
            import clip
            model, preprocess = clip.load("ViT-B/32", device=self.device)
            return model, preprocess
        except ImportError:
            logger.warning("CLIP not available - vision-language features will be limited")
            return None, None
        except Exception as e:
            logger.error(f"Failed to load CLIP model: {e}")
            return None, None
    
    def _load_blip_model(self) -> Optional[dict]:
        """Load BLIP model for visual question answering and captioning."""
        try:
            from transformers import BlipProcessor, BlipForConditionalGeneration
            
            processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
            model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(self.device)
            
            return {"processor": processor, "model": model}
        except ImportError:
            logger.warning("BLIP not available - visual QA and captioning will be limited")
            return None
        except Exception as e:
            logger.error(f"Failed to load BLIP model: {e}")
            return None
    
    def analyze_image_text(self, image: Image.Image, text: str) -> Dict[str, Any]:
        """
        Analyze relationship between image and text.
        
        Args:
            image: PIL Image to analyze
            text: Text to compare with image
            
        Returns:
            Dictionary with similarity score, features, and interpretation
        """
        if not self.clip_model:
            return {"error": "CLIP model not available", "available": False}
        
        try:
            # Preprocess image
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)
            text_input = clip.tokenize([text]).to(self.device)
            
            # Get features
            with torch.no_grad():
                image_features = self.clip_model.encode_image(image_input)
                text_features = self.clip_model.encode_text(text_input)
            
            # Calculate similarity
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            similarity = (image_features @ text_features.T).item()
            
            return {
                "success": True,
                "similarity_score": float(similarity),
                "image_features": image_features.cpu().numpy().tolist(),
                "text_features": text_features.cpu().numpy().tolist(),
                "interpretation": self._interpret_similarity(similarity),
                "available": True
            }
        except Exception as e:
            logger.error(f"Image-text analysis failed: {e}")
            return {"error": str(e), "success": False, "available": False}
    
    def _interpret_similarity(self, score: float) -> str:
        """Interpret similarity score with human-readable labels."""
        if score > 0.8:
            return "strong_match"
        elif score > 0.6:
            return "moderate_match"
        elif score > 0.4:
            return "weak_match"
        elif score > 0.2:
            return "minimal_match"
        else:
            return "no_match"
    
    def visual_question_answering(self, image: Image.Image, question: str) -> Dict[str, Any]:
        """
        Answer questions about visual content using BLIP.
        
        Args:
            image: PIL Image containing visual content
            question: Question about the image
            
        Returns:
            Dictionary with answer and success status
        """
        if not self.blip_model:
            return {"answer": "Visual QA not available", "success": False, "available": False}
        
        try:
            processor = self.blip_model["processor"]
            model = self.blip_model["model"]
            
            inputs = processor(image, question, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                outputs = model.generate(**inputs, max_new_tokens=50)
            
            answer = processor.decode(outputs[0], skip_special_tokens=True)
            
            return {
                "answer": answer,
                "success": True,
                "available": True,
                "model": "BLIP"
            }
        except Exception as e:
            logger.error(f"Visual QA failed: {e}")
            return {"answer": "Sorry, I couldn't process that visual question.", "success": False, "available": False}
    
    def generate_image_caption(self, image: Image.Image) -> Dict[str, Any]:
        """
        Generate descriptive caption for image using BLIP.
        
        Args:
            image: PIL Image to caption
            
        Returns:
            Dictionary with caption and success status
        """
        if not self.blip_model:
            return {"caption": "Image captioning not available", "success": False, "available": False}
        
        try:
            processor = self.blip_model["processor"]
            model = self.blip_model["model"]
            
            inputs = processor(image, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                outputs = model.generate(**inputs, max_new_tokens=20)
            
            caption = processor.decode(outputs[0], skip_special_tokens=True)
            
            return {
                "caption": caption,
                "success": True,
                "available": True,
                "model": "BLIP"
            }
        except Exception as e:
            logger.error(f"Caption generation failed: {e}")
            return {"caption": "Sorry, I couldn't generate a caption for this image.", "success": False, "available": False}
    
    def create_multimodal_embedding(self, image: Image.Image, text: str) -> Dict[str, Any]:
        """
        Create combined multimodal embedding.
        
        Args:
            image: PIL Image
            text: Associated text
            
        Returns:
            Dictionary with embedding array and success status
        """
        if not self.clip_model:
            return {"error": "CLIP model not available", "success": False, "available": False}
        
        try:
            # Get individual embeddings
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)
            text_input = clip.tokenize([text]).to(self.device)
            
            with torch.no_grad():
                image_features = self.clip_model.encode_image(image_input)
                text_features = self.clip_model.encode_text(text_input)
            
            # Combine embeddings
            combined = torch.cat([image_features, text_features], dim=1)
            
            return {
                "embedding": combined.cpu().numpy().tolist(),
                "image_embedding": image_features.cpu().numpy().tolist(),
                "text_embedding": text_features.cpu().numpy().tolist(),
                "embedding_dim": combined.shape[1],
                "success": True,
                "available": True
            }
        except Exception as e:
            logger.error(f"Multimodal embedding creation failed: {e}")
            return {"error": str(e), "success": False, "available": False}
    
    def analyze_scene_with_context(self, image: Image.Image, context_text: str) -> Dict[str, Any]:
        """
        Comprehensive scene analysis with multimodal understanding.
        
        Args:
            image: PIL Image of the scene
            context_text: Contextual information about the scene
            
        Returns:
            Comprehensive analysis including visual and multimodal data
        """
        result = {
            "timestamp": time.time(),
            "multimodal_available": self.clip_model is not None,
            "visual_qa_available": self.blip_model is not None
        }
        
        # Basic visual analysis (would integrate with Observer)
        result["visual_analysis"] = {
            "width": image.width,
            "height": image.height,
            "mode": image.mode
        }
        
        # Multimodal analysis
        if self.clip_model:
            multimodal_result = self.analyze_image_text(image, context_text)
            result["multimodal"] = multimodal_result
        
        # Visual QA and captioning
        if self.blip_model:
            caption_result = self.generate_image_caption(image)
            result["caption"] = caption_result.get("caption", "")
            
            # Ask a generic question about the scene
            vqa_result = self.visual_question_answering(image, "What is happening in this image?")
            result["scene_description"] = vqa_result.get("answer", "")
        
        return result
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Return current capabilities and availability status."""
        return {
            "clip_available": self.clip_model is not None,
            "blip_available": self.blip_model is not None,
            "device": self.device,
            "multimodal_analysis": self.clip_model is not None,
            "visual_qa": self.blip_model is not None,
            "image_captioning": self.blip_model is not None,
            "embedding_creation": self.clip_model is not None,
            "initialized": self.initialized
        }
    
    def clear_cache(self):
        """Clear any cached results."""
        self.cache = {}
        logger.info("Multimodal agent cache cleared")

# Fallback implementation for when models are not available
class SimpleMultimodalAgent:
    """Fallback multimodal agent with basic capabilities."""
    
    def __init__(self):
        self.available = False
        logger.warning("Using fallback SimpleMultimodalAgent - install CLIP and BLIP for full capabilities")
    
    def analyze_image_text(self, image: Image.Image, text: str) -> Dict[str, Any]:
        return {
            "error": "Full multimodal analysis not available",
            "success": False,
            "available": False,
            "fallback": True
        }
    
    def visual_question_answering(self, image: Image.Image, question: str) -> Dict[str, Any]:
        return {
            "answer": "Visual question answering not available in fallback mode",
            "success": False,
            "available": False,
            "fallback": True
        }
    
    def generate_image_caption(self, image: Image.Image) -> Dict[str, Any]:
        return {
            "caption": "Basic image detected",
            "success": True,
            "available": False,
            "fallback": True
        }
    
    def create_multimodal_embedding(self, image: Image.Image, text: str) -> Dict[str, Any]:
        return {
            "error": "Embedding creation not available in fallback mode",
            "success": False,
            "available": False,
            "fallback": True
        }
    
    def get_capabilities(self) -> Dict[str, Any]:
        return {
            "clip_available": False,
            "blip_available": False,
            "fallback_mode": True,
            "limited_capabilities": True
        }

# Factory function to create appropriate agent
def create_multimodal_agent(use_fallback: bool = False) -> MultimodalAgent:
    """Create multimodal agent, with fallback option."""
    if use_fallback:
        return SimpleMultimodalAgent()
    
    try:
        return MultimodalAgent()
    except Exception as e:
        logger.error(f"Failed to create full MultimodalAgent: {e}")
        return SimpleMultimodalAgent()

if __name__ == "__main__":
    # Test the agent
    import time
    from PIL import Image
    
    print("Testing MultimodalAgent...")
    agent = create_multimodal_agent()
    
    # Create test image
    test_image = Image.new('RGB', (224, 224), color='blue')
    
    # Test capabilities
    caps = agent.get_capabilities()
    print(f"Capabilities: {caps}")
    
    # Test image captioning
    caption_result = agent.generate_image_caption(test_image)
    print(f"Caption: {caption_result}")
    
    # Test multimodal analysis
    analysis = agent.analyze_image_text(test_image, "a blue square")
    print(f"Analysis: {analysis}")
    
    print("Test complete!")