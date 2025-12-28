"""
Remote Access Module for ARCHER.

Secure remote interaction via smartphone/web interface using WireGuard/ZeroTier.
Enhanced implementation with full API, security, and mobile integration.
"""

import logging
import os
import subprocess
import threading
import json
import time
import socket
import hashlib
from typing import Optional, Dict, List, Any
from pathlib import Path
from datetime import datetime

try:
    from fastapi import FastAPI, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    logging.warning("FastAPI not available - remote access disabled")

logger = logging.getLogger(__name__)


class RemoteAccessSecurity:
    """Security utilities for remote access."""
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key."""
        return hashlib.sha256(os.urandom(32)).hexdigest()
    
    @staticmethod
    def validate_ip(ip: str, allowed_networks: List[str]) -> bool:
        """Validate IP against allowed networks."""
        if not allowed_networks:
            return True
        
        try:
            # Simple IP validation - enhance with proper CIDR parsing
            return any(ip.startswith(net.strip()) for net in allowed_networks if net.strip())
        except:
            return False
    
    @staticmethod
    def log_security_event(event_type: str, details: Dict[str, Any]):
        """Log security events."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "details": details,
            "severity": "info"
        }
        
        # Log to file
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        with open(log_dir / "remote_access_security.log", "a") as f:
            f.write(json.dumps(log_entry) + "\n")


class RemoteAccessServer:
    """
    Secure remote access server using WireGuard/ZeroTier.

    Features:
    - REST API for remote commands
    - WebSocket for real-time updates
    - Secure tunnel authentication
    - Mobile app integration
    - Comprehensive security logging
    """

    def __init__(self, port: int = 8080):
        self.port = port
        self.app: Optional[FastAPI] = None
        self.server_thread: Optional[threading.Thread] = None
        self.running = False
        self.tunnel_active = False
        self.connected_clients: Dict[str, Dict[str, Any]] = {}
        
        # Security
        self.api_key = os.getenv("REMOTE_API_KEY", RemoteAccessSecurity.generate_api_key())
        self.allowed_networks = os.getenv("ALLOWED_NETWORKS", "").split(",")
        self.security = RemoteAccessSecurity()
        
        # WireGuard/ZeroTier config
        self.tunnel_type = os.getenv("TUNNEL_TYPE", "wireguard")  # wireguard or zerotier
        self.tunnel_config = Path("config") / f"{self.tunnel_type}.conf"
        self.tunnel_interface = "wg0" if self.tunnel_type == "wireguard" else "zt0"
        
        # WebSocket connections
        self.active_websockets: List[WebSocket] = []
        
        if FASTAPI_AVAILABLE:
            self._setup_api()
            logger.info(f"Remote access server initialized - Port {port}")
            logger.info(f"API Key: {self.api_key}")
            logger.info(f"Tunnel Type: {self.tunnel_type}")
        else:
            logger.warning("Remote access requires FastAPI - install with: pip install fastapi uvicorn")

    def _setup_api(self):
        """Setup FastAPI application with comprehensive API."""
        self.app = FastAPI(title="ARCHER Remote API", version="1.0.0")

        # CORS configuration
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Restrict in production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Security
        security = HTTPBearer()

        async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
            if credentials.credentials != self.api_key:
                self.security.log_security_event("auth_failed", {
                    "attempted_key": credentials.credentials[:8] + "...",
                    "client_ip": "unknown"
                })
                raise HTTPException(status_code=401, detail="Invalid API key")
            return credentials.credentials

        async def verify_ip(request: Request):
            """Verify client IP against allowed networks."""
            client_ip = request.client.host
            if not self.security.validate_ip(client_ip, self.allowed_networks):
                self.security.log_security_event("ip_blocked", {
                    "client_ip": client_ip,
                    "allowed_networks": self.allowed_networks
                })
                raise HTTPException(status_code=403, detail="IP not allowed")

        # Status Endpoints
        @self.app.get("/status")
        async def get_status(api_key: str = Depends(verify_api_key)):
            """Get ARCHER system status."""
            return {
                "status": "online",
                "tunnel": self.tunnel_type,
                "tunnel_active": self.tunnel_active,
                "connected_clients": len(self.connected_clients),
                "timestamp": datetime.now().isoformat()
            }

        @self.app.get("/tunnel/status")
        async def get_tunnel_status(api_key: str = Depends(verify_api_key)):
            """Get tunnel-specific status."""
            status = {
                "type": self.tunnel_type,
                "active": self.tunnel_active,
                "interface": self.tunnel_interface
            }
            
            if self.tunnel_type == "wireguard":
                status.update(self._get_wireguard_status())
            elif self.tunnel_type == "zerotier":
                status.update(self._get_zerotier_status())
                
            return status

        # Command Execution
        @self.app.post("/command")
        async def execute_command(
            command: dict,
            api_key: str = Depends(verify_api_key),
            _ip_verified: bool = Depends(verify_ip)
        ):
            """Execute remote commands securely."""
            if not command or "action" not in command:
                raise HTTPException(status_code=400, detail="Invalid command format")
            
            # Log the command
            self.security.log_security_event("command_executed", {
                "action": command["action"],
                "params": str(command.get("params", {}))
            })
            
            # Placeholder - integrate with ARCHER core
            logger.info(f"Remote command: {command}")
            
            # Broadcast to WebSocket clients
            await self._broadcast_websocket({
                "type": "command_execution",
                "data": {"action": command["action"], "status": "received"}
            })
            
            return {
                "result": "Command received and queued",
                "command_id": hashlib.md5(json.dumps(command).encode()).hexdigest(),
                "timestamp": datetime.now().isoformat()
            }

        # Log Retrieval
        @self.app.get("/logs")
        async def get_logs(
            limit: int = 50,
            api_key: str = Depends(verify_api_key)
        ):
            """Get recent logs."""
            try:
                log_file = Path("logs/voice_auth.log")
                if log_file.exists():
                    with open(log_file, 'r') as f:
                        logs = f.readlines()[-limit:]
                    return {"logs": logs, "count": len(logs)}
                else:
                    return {"logs": [], "count": 0, "message": "No logs found"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error reading logs: {str(e)}")

        @self.app.get("/security/logs")
        async def get_security_logs(
            limit: int = 50,
            api_key: str = Depends(verify_api_key)
        ):
            """Get security logs."""
            try:
                log_file = Path("logs/remote_access_security.log")
                if log_file.exists():
                    with open(log_file, 'r') as f:
                        logs = [json.loads(line) for line in f.readlines()[-limit:]]
                    return {"logs": logs, "count": len(logs)}
                else:
                    return {"logs": [], "count": 0, "message": "No security logs found"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error reading security logs: {str(e)}")

        # System Information
        @self.app.get("/system/info")
        async def get_system_info(api_key: str = Depends(verify_api_key)):
            """Get system information."""
            return {
                "system": "ARCHER Remote Access",
                "version": "1.0.0",
                "tunnel": self.tunnel_type,
                "api_version": "1.0",
                "capabilities": [
                    "voice_commands",
                    "status_monitoring",
                    "log_retrieval",
                    "real_time_updates"
                ]
            }

        # WebSocket for real-time updates
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates."""
            await websocket.accept()
            self.active_websockets.append(websocket)
            
            client_id = hashlib.md5(str(time.time()).encode()).hexdigest()
            self.connected_clients[client_id] = {
                "connected_at": datetime.now().isoformat(),
                "websocket": websocket
            }
            
            logger.info(f"WebSocket client connected: {client_id}")
            
            try:
                while True:
                    data = await websocket.receive_text()
                    try:
                        message = json.loads(data)
                        logger.info(f"WebSocket message: {message}")
                        
                        # Handle ping/pong
                        if message.get("type") == "ping":
                            await websocket.send_text(json.dumps({
                                "type": "pong",
                                "timestamp": datetime.now().isoformat()
                            }))
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid WebSocket message: {data}")
            except WebSocketDisconnect:
                logger.info(f"WebSocket client disconnected: {client_id}")
                self.active_websockets.remove(websocket)
                del self.connected_clients[client_id]

        # Mobile-specific endpoints
        @self.app.post("/mobile/command")
        async def mobile_command(
            command: dict,
            api_key: str = Depends(verify_api_key)
        ):
            """Mobile-optimized command endpoint."""
            if not command or "action" not in command:
                raise HTTPException(status_code=400, detail="Invalid command")
            
            # Validate mobile-specific commands
            valid_mobile_actions = ["voice_command", "status_check", "get_logs", "emergency_stop"]
            if command["action"] not in valid_mobile_actions:
                raise HTTPException(status_code=400, detail=f"Invalid mobile action: {command['action']}")
            
            # Process voice commands
            if command["action"] == "voice_command":
                text = command.get("text", "")
                if not text:
                    raise HTTPException(status_code=400, detail="Voice command text required")
                
                # Log to voice auth log as requested
                self._log_voice_command(text)
                
                return {
                    "status": "voice_command_received",
                    "text": text,
                    "timestamp": datetime.now().isoformat()
                }
            
            return {
                "status": "mobile_command_processed",
                "action": command["action"],
                "timestamp": datetime.now().isoformat()
            }

        # Setup static files for web interface
        self.app.mount("/static", StaticFiles(directory="src/web/interface"), name="static")

    def _log_voice_command(self, text: str):
        """Log voice commands to voice_auth.log as specified."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        log_entry = f"{datetime.now().isoformat()} - REMOTE VOICE COMMAND: {text}\n"
        
        with open(log_dir / "voice_auth.log", "a") as f:
            f.write(log_entry)
        
        logger.info(f"Logged remote voice command: {text[:50]}...")

    async def _broadcast_websocket(self, message: Dict[str, Any]):
        """Broadcast message to all connected WebSocket clients."""
        for ws in self.active_websockets:
            try:
                await ws.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"WebSocket broadcast failed: {e}")
                # Remove failed connection
                self.active_websockets.remove(ws)

    def _get_wireguard_status(self) -> Dict[str, Any]:
        """Get WireGuard tunnel status."""
        status = {"peers": [], "rx_bytes": 0, "tx_bytes": 0}
        
        try:
            result = subprocess.run(
                ["wg", "show", self.tunnel_interface],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse WireGuard output
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                # Parse interface stats
                interface_line = lines[0]
                # Example: "interface: wg0\n  public key: ...\n  private key: (hidden)"
                
                # Parse peer stats
                for line in lines[2:]:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 5:
                            peer = {
                                "public_key": parts[0],
                                "endpoint": parts[2] if len(parts) > 2 else "unknown",
                                "allowed_ips": parts[3] if len(parts) > 3 else "unknown",
                                "latest_handshake": parts[4] if len(parts) > 4 else "unknown"
                            }
                            status["peers"].append(peer)
        except Exception as e:
            logger.warning(f"Failed to get WireGuard status: {e}")
        
        return status

    def _get_zerotier_status(self) -> Dict[str, Any]:
        """Get ZeroTier network status."""
        status = {"networks": [], "peers": [], "online": False}
        
        try:
            # Get network status
            result = subprocess.run(
                ["zerotier-cli", "listnetworks"],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse network info
            lines = result.stdout.strip().split('\n')
            for line in lines[1:]:  # Skip header
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 5:
                        network = {
                            "nwid": parts[0],
                            "name": parts[1] if len(parts) > 1 else "unknown",
                            "mac": parts[2] if len(parts) > 2 else "unknown",
                            "status": parts[3] if len(parts) > 3 else "unknown",
                            "type": parts[4] if len(parts) > 4 else "unknown"
                        }
                        status["networks"].append(network)
                        if network["status"] == "OK":
                            status["online"] = True
            
            # Get peer status
            result = subprocess.run(
                ["zerotier-cli", "listpeers"],
                capture_output=True,
                text=True,
                check=True
            )
            
            lines = result.stdout.strip().split('\n')
            for line in lines[1:]:  # Skip header
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 6:
                        peer = {
                            "address": parts[0],
                            "path": parts[1] if len(parts) > 1 else "unknown",
                            "latency": parts[2] if len(parts) > 2 else "unknown",
                            "version": parts[3] if len(parts) > 3 else "unknown",
                            "role": parts[4] if len(parts) > 4 else "unknown"
                        }
                        status["peers"].append(peer)
        except Exception as e:
            logger.warning(f"Failed to get ZeroTier status: {e}")
        
        return status

    def start(self):
        """Start the remote access server and tunnel."""
        if not FASTAPI_AVAILABLE:
            logger.error("Cannot start remote access - FastAPI not available")
            return

        logger.info("Starting remote access server...")

        # Start tunnel
        self._start_tunnel()

        # Start API server in thread
        self.running = True
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()

        logger.info(f"✓ Remote access server started on port {self.port}")
        logger.info(f"✓ API available at http://localhost:{self.port}")
        logger.info(f"✓ WebSocket available at ws://localhost:{self.port}/ws")

    def _start_tunnel(self):
        """Start WireGuard or ZeroTier tunnel with enhanced error handling."""
        try:
            if self.tunnel_type == "wireguard":
                # Check if WireGuard is installed
                try:
                    subprocess.run(["wg", "--version"], capture_output=True, check=True)
                except:
                    logger.error("WireGuard not installed. Install with: sudo apt install wireguard")
                    return
                
                # Generate config if needed
                if not self.tunnel_config.exists():
                    logger.warning(f"WireGuard config not found at {self.tunnel_config}")
                    logger.info("Creating default WireGuard config...")
                    self._generate_wireguard_config()
                
                # Start WireGuard
                try:
                    result = subprocess.run(
                        ["wg-quick", "up", str(self.tunnel_config)],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    logger.info("WireGuard tunnel started")
                    logger.info(f"Interface: {self.tunnel_interface}")
                    self.tunnel_active = True
                    
                    # Get interface IP
                    try:
                        result = subprocess.run(
                            ["ip", "addr", "show", self.tunnel_interface],
                            capture_output=True,
                            text=True,
                            check=True
                        )
                        for line in result.stdout.split('\n'):
                            if 'inet ' in line:
                                ip_info = line.strip().split()
                                if len(ip_info) >= 2:
                                    logger.info(f"Tunnel IP: {ip_info[1].split('/')[0]}")
                                    break
                    except Exception as e:
                        logger.warning(f"Could not determine tunnel IP: {e}")
                        
                except subprocess.CalledProcessError as e:
                    logger.error(f"Failed to start WireGuard: {e.stderr}")
                    return
                    
            elif self.tunnel_type == "zerotier":
                # Check if ZeroTier is installed
                try:
                    subprocess.run(["zerotier-cli", "version"], capture_output=True, check=True)
                except:
                    logger.error("ZeroTier not installed. Install from https://www.zerotier.com/")
                    return
                
                network_id = os.getenv("ZEROTIER_NETWORK_ID")
                if not network_id:
                    logger.error("ZeroTier network ID not set. Configure ZEROTIER_NETWORK_ID environment variable.")
                    return
                
                try:
                    # Join network
                    result = subprocess.run(
                        ["zerotier-cli", "join", network_id],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    logger.info("ZeroTier network joined")
                    logger.info(f"Network ID: {network_id}")
                    
                    # Check status
                    time.sleep(2)  # Wait for connection
                    result = subprocess.run(
                        ["zerotier-cli", "listnetworks"],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    
                    # Parse to find our network status
                    for line in result.stdout.split('\n'):
                        if network_id in line and 'OK' in line:
                            self.tunnel_active = True
                            logger.info("ZeroTier connection established")
                            break
                    
                    if not self.tunnel_active:
                        logger.warning("ZeroTier connection not yet established. Check ZeroTier Central.")
                        
                except subprocess.CalledProcessError as e:
                    logger.error(f"Failed to join ZeroTier network: {e.stderr}")
                    return
        except Exception as e:
            logger.error(f"Failed to start tunnel: {e}")

    def _generate_wireguard_config(self):
        """Generate a basic WireGuard configuration."""
        try:
            # Generate private key
            result = subprocess.run(
                ["wg", "genkey"],
                capture_output=True,
                text=True,
                check=True
            )
            private_key = result.stdout.strip()
            
            # Generate public key
            result = subprocess.run(
                ["wg", "pubkey"],
                input=private_key,
                capture_output=True,
                text=True,
                check=True
            )
            public_key = result.stdout.strip()
            
            # Create config
            config_content = f"""# ARCHER WireGuard Configuration - Generated {datetime.now().isoformat()}
[Interface]
PrivateKey = {private_key}
Address = 10.8.0.1/24
ListenPort = 51820
DNS = 8.8.8.8, 8.8.4.4

# NAT and forwarding
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

PersistentKeepalive = 25

# Client placeholder - replace with actual client public key
# [Peer]
# PublicKey = CLIENT_PUBLIC_KEY
# AllowedIPs = 10.8.0.2/32
"""
            
            with open(self.tunnel_config, 'w') as f:
                f.write(config_content)
                
            logger.info(f"Generated WireGuard config at {self.tunnel_config}")
            logger.info(f"Server Public Key: {public_key}")
            logger.info("Add client peers to the config file and restart the tunnel.")
            
        except Exception as e:
            logger.error(f"Failed to generate WireGuard config: {e}")

    def _run_server(self):
        """Run the FastAPI server with enhanced logging."""
        try:
            logger.info(f"Starting FastAPI server on 0.0.0.0:{self.port}")
            uvicorn.run(
                self.app,
                host="0.0.0.0",
                port=self.port,
                log_level="info",
                access_log=True
            )
        except Exception as e:
            logger.error(f"API server failed: {e}")
            self.running = False

    def stop(self):
        """Stop the remote access server and tunnel."""
        logger.info("Stopping remote access server...")

        self.running = False
        self.tunnel_active = False

        # Stop tunnel
        self._stop_tunnel()

        # Stop server thread
        if self.server_thread and self.server_thread.is_alive():
            # Give thread time to shut down gracefully
            self.server_thread.join(timeout=10)
            if self.server_thread.is_alive():
                logger.warning("Server thread did not stop gracefully")

        # Close WebSocket connections
        for ws in self.active_websockets:
            try:
                ws.close()
            except:
                pass
        
        self.active_websockets.clear()
        self.connected_clients.clear()

        logger.info("✓ Remote access server stopped")

    def _stop_tunnel(self):
        """Stop the tunnel with enhanced error handling."""
        try:
            if self.tunnel_type == "wireguard":
                try:
                    result = subprocess.run(
                        ["wg-quick", "down", str(self.tunnel_config)],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    logger.info("WireGuard tunnel stopped")
                except subprocess.CalledProcessError as e:
                    logger.error(f"Failed to stop WireGuard: {e.stderr}")
            elif self.tunnel_type == "zerotier":
                network_id = os.getenv("ZEROTIER_NETWORK_ID")
                if network_id:
                    try:
                        result = subprocess.run(
                            ["zerotier-cli", "leave", network_id],
                            capture_output=True,
                            text=True,
                            check=True
                        )
                        logger.info("ZeroTier network left")
                    except subprocess.CalledProcessError as e:
                        logger.error(f"Failed to leave ZeroTier network: {e.stderr}")
        except Exception as e:
            logger.error(f"Failed to stop tunnel: {e}")

    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for client setup."""
        info = {
            "tunnel_type": self.tunnel_type,
            "server_port": self.port,
            "api_key": self.api_key[:8] + "..." + self.api_key[-4:],
            "status": "online" if self.running else "offline",
            "tunnel_active": self.tunnel_active
        }
        
        if self.tunnel_type == "wireguard":
            if self.tunnel_config.exists():
                try:
                    # Extract public key from config
                    with open(self.tunnel_config, 'r') as f:
                        for line in f:
                            if line.startswith('PrivateKey'):
                                # We could extract and generate public key, but for security don't expose it
                                break
                except:
                    pass
                
                info.update({
                    "wireguard_config": str(self.tunnel_config),
                    "interface": self.tunnel_interface,
                    "listen_port": 51820
                })
        elif self.tunnel_type == "zerotier":
            network_id = os.getenv("ZEROTIER_NETWORK_ID", "")
            info.update({
                "zerotier_network_id": network_id[:8] + "..." + network_id[-4:] if network_id else "not_configured"
            })
        
        return info

    def generate_client_config(self, client_name: str = "mobile") -> Dict[str, Any]:
        """Generate client configuration for mobile setup."""
        config = {
            "client_name": client_name,
            "server_address": self._get_public_ip(),
            "server_port": self.port,
            "api_key": self.api_key,
            "tunnel_type": self.tunnel_type
        }
        
        if self.tunnel_type == "wireguard":
            config.update({
                "wireguard": {
                    "server_public_key": "GENERATE_AND_ADD_TO_SERVER_CONFIG",
                    "server_endpoint": f"{self._get_public_ip()}:51820",
                    "client_address": "10.8.0.2/32",
                    "dns": "8.8.8.8, 8.8.4.4"
                }
            })
        elif self.tunnel_type == "zerotier":
            network_id = os.getenv("ZEROTIER_NETWORK_ID", "")
            config.update({
                "zerotier": {
                    "network_id": network_id,
                    "auth_required": True
                }
            })
        
        return config

    def _get_public_ip(self) -> str:
        """Get public IP address for client configuration."""
        try:
            # Try to get public IP (simple method - may need enhancement)
            result = subprocess.run(
                ["curl", "-s", "https://api.ipify.org"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        # Fallback to localhost for testing
        return "localhost"


# Global instance for easy access
remote_access_server = None


def start_remote_access():
    """Start the remote access server."""
    global remote_access_server
    if remote_access_server is None:
        remote_access_server = RemoteAccessServer()
    remote_access_server.start()


def stop_remote_access():
    """Stop the remote access server."""
    global remote_access_server
    if remote_access_server and remote_access_server.running:
        remote_access_server.stop()


def get_remote_access_status():
    """Get remote access status."""
    global remote_access_server
    if remote_access_server:
        return remote_access_server.get_connection_info()
    return {"status": "not_initialized"}
