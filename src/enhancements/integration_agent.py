"""
Integration Agent

Handles tool and workflow integrations for ARCHER including:
- Google Drive integration
- CRM systems
- Schedulers
- External APIs
- Plugin architecture for extensibility
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Import external libraries
import httpx
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)


@dataclass
class ToolConfig:
    """Configuration for an external tool integration."""
    name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    auth_type: str = "none"  # none, api_key, oauth2, basic
    username: Optional[str] = None
    password: Optional[str] = None
    scopes: Optional[List[str]] = None
    enabled: bool = True


class BaseToolIntegration(ABC):
    """Abstract base class for tool integrations."""
    
    def __init__(self, config: ToolConfig):
        self.config = config
        self.client = None
        self._initialize_client()
    
    @abstractmethod
    def _initialize_client(self):
        """Initialize the client for this tool."""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test the connection to the tool."""
        pass
    
    @abstractmethod
    def execute(self, action: str, **kwargs) -> Any:
        """Execute an action on the tool."""
        pass


class GoogleDriveIntegration(BaseToolIntegration):
    """Integration with Google Drive."""
    
    def __init__(self, config: ToolConfig):
        super().__init__(config)
        self.credentials = None
        self.service = None
    
    def _initialize_client(self):
        """Initialize Google Drive client using OAuth2."""
        try:
            # Check if we have cached credentials
            creds_path = Path("~/.archer/google_drive_creds.json").expanduser()
            
            if creds_path.exists():
                self.credentials = Credentials.from_authorized_user_file(str(creds_path), 
                                                                       self.config.scopes or [])
            
            # If credentials are invalid or don't exist, run OAuth flow
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'credentials.json', 
                        scopes=self.config.scopes or [
                            'https://www.googleapis.com/auth/drive.file',
                            'https://www.googleapis.com/auth/drive.metadata.readonly'
                        ]
                    )
                    self.credentials = flow.run_local_server(port=0)
                    
                    # Save credentials for next time
                    creds_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(creds_path, 'w') as token:
                        token.write(self.credentials.to_json())
            
            # Build the service
            self.service = build('drive', 'v3', credentials=self.credentials)
            logger.info("Google Drive client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive client: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test the connection to Google Drive."""
        try:
            if not self.service:
                return False
            
            # Try to get basic info about the drive
            about = self.service.about().get(fields="user").execute()
            logger.info(f"Connected to Google Drive as: {about['user']['emailAddress']}")
            return True
        except Exception as e:
            logger.error(f"Google Drive connection test failed: {e}")
            return False
    
    def execute(self, action: str, **kwargs) -> Any:
        """Execute Google Drive actions."""
        if not self.service:
            raise Exception("Google Drive service not initialized")
        
        try:
            if action == "list_files":
                return self._list_files(**kwargs)
            elif action == "upload_file":
                return self._upload_file(**kwargs)
            elif action == "download_file":
                return self._download_file(**kwargs)
            elif action == "search_files":
                return self._search_files(**kwargs)
            else:
                raise ValueError(f"Unknown action: {action}")
        except Exception as e:
            logger.error(f"Google Drive action '{action}' failed: {e}")
            raise
    
    def _list_files(self, folder_id: str = "root", max_results: int = 10) -> List[Dict]:
        """List files in a folder."""
        results = self.service.files().list(
            q=f"'{folder_id}' in parents",
            pageSize=max_results,
            fields="files(id, name, mimeType, size, createdTime)"
        ).execute()
        return results.get('files', [])
    
    def _upload_file(self, file_path: str, folder_id: str = "root", file_name: str = None) -> Dict:
        """Upload a file to Google Drive."""
        file_path = Path(file_path)
        file_name = file_name or file_path.name
        
        file_metadata = {
            'name': file_name,
            'parents': [folder_id] if folder_id != "root" else []
        }
        
        media = MediaFileUpload(str(file_path), resumable=True)
        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, mimeType, size'
        ).execute()
        
        logger.info(f"Uploaded file: {file['name']} (ID: {file['id']})")
        return file
    
    def _download_file(self, file_id: str, download_path: str) -> str:
        """Download a file from Google Drive."""
        request = self.service.files().get_media(fileId=file_id)
        
        download_path = Path(download_path)
        download_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(download_path, 'wb') as f:
            f.write(request.execute())
        
        logger.info(f"Downloaded file to: {download_path}")
        return str(download_path)
    
    def _search_files(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search for files using a query."""
        results = self.service.files().list(
            q=query,
            pageSize=max_results,
            fields="files(id, name, mimeType, size, createdTime)"
        ).execute()
        return results.get('files', [])


class RESTAPIIntegration(BaseToolIntegration):
    """Generic REST API integration."""
    
    def __init__(self, config: ToolConfig):
        super().__init__(config)
        self.timeout = 30
    
    def _initialize_client(self):
        """Initialize HTTP client."""
        headers = {}
        
        if self.config.auth_type == "api_key":
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
        elif self.config.auth_type == "basic":
            if self.config.username and self.config.password:
                import base64
                credentials = base64.b64encode(f"{self.config.username}:{self.config.password}".encode()).decode()
                headers["Authorization"] = f"Basic {credentials}"
        
        self.client = httpx.Client(
            base_url=self.config.base_url,
            headers=headers,
            timeout=self.timeout
        )
    
    def test_connection(self) -> bool:
        """Test the API connection."""
        try:
            response = self.client.get("/")
            return response.status_code < 400
        except Exception as e:
            logger.error(f"API connection test failed: {e}")
            return False
    
    def execute(self, action: str, **kwargs) -> Any:
        """Execute API actions."""
        method = kwargs.get('method', 'GET').upper()
        endpoint = kwargs.get('endpoint', '')
        data = kwargs.get('data', {})
        params = kwargs.get('params', {})
        
        try:
            if method == 'GET':
                response = self.client.get(endpoint, params=params)
            elif method == 'POST':
                response = self.client.post(endpoint, json=data)
            elif method == 'PUT':
                response = self.client.put(endpoint, json=data)
            elif method == 'DELETE':
                response = self.client.delete(endpoint)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"API request failed: {e}")
            raise


class IntegrationAgent:
    """Main integration agent that manages all tool integrations."""
    
    def __init__(self):
        self.tools: Dict[str, BaseToolIntegration] = {}
        self.config_file = Path("config/integrations.json")
        self._load_configurations()
    
    def _load_configurations(self):
        """Load tool configurations from file."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    configs = json.load(f)
                    
                for tool_name, tool_config in configs.items():
                    try:
                        config = ToolConfig(**tool_config)
                        self.register_tool(tool_name, config)
                    except Exception as e:
                        logger.error(f"Failed to load tool {tool_name}: {e}")
            else:
                logger.info("No integrations config file found, starting with empty tools")
        except Exception as e:
            logger.error(f"Failed to load integrations config: {e}")
    
    def register_tool(self, tool_name: str, config: ToolConfig):
        """Register a new tool integration."""
        try:
            if tool_name in self.tools:
                logger.warning(f"Tool {tool_name} already registered, replacing")
            
            # Create the appropriate integration
            if "google_drive" in tool_name.lower():
                integration = GoogleDriveIntegration(config)
            else:
                integration = RESTAPIIntegration(config)
            
            self.tools[tool_name] = integration
            logger.info(f"Registered tool: {tool_name}")
            
            # Test the connection
            if config.enabled:
                if integration.test_connection():
                    logger.info(f"✓ {tool_name} connection successful")
                else:
                    logger.warning(f"✗ {tool_name} connection failed")
            
        except Exception as e:
            logger.error(f"Failed to register tool {tool_name}: {e}")
    
    def get_tool(self, tool_name: str) -> Optional[BaseToolIntegration]:
        """Get a registered tool by name."""
        return self.tools.get(tool_name)
    
    def execute_tool_action(self, tool_name: str, action: str, **kwargs) -> Any:
        """Execute an action on a specific tool."""
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found")
        
        return tool.execute(action, **kwargs)
    
    def list_available_tools(self) -> List[str]:
        """List all available tools."""
        return list(self.tools.keys())
    
    def save_configurations(self):
        """Save current tool configurations to file."""
        try:
            configs = {}
            for tool_name, tool in self.tools.items():
                configs[tool_name] = {
                    "name": tool.config.name,
                    "api_key": tool.config.api_key,
                    "base_url": tool.config.base_url,
                    "auth_type": tool.config.auth_type,
                    "username": tool.config.username,
                    "password": tool.config.password,
                    "scopes": tool.config.scopes,
                    "enabled": tool.config.enabled
                }
            
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(configs, f, indent=2)
            
            logger.info(f"Saved {len(configs)} tool configurations")
        except Exception as e:
            logger.error(f"Failed to save configurations: {e}")
    
    def shutdown(self):
        """Clean up all tool integrations."""
        for tool_name, tool in self.tools.items():
            try:
                if hasattr(tool, 'close'):
                    tool.close()
                logger.info(f"Shut down tool: {tool_name}")
            except Exception as e:
                logger.error(f"Error shutting down {tool_name}: {e}")
        
        self.tools.clear()


# Example usage and testing
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Create integration agent
    agent = IntegrationAgent()
    
    # Example: Register a REST API tool
    api_config = ToolConfig(
        name="example_api",
        base_url="https://api.example.com/v1",
        auth_type="api_key",
        api_key="your_api_key_here",
        enabled=True
    )
    
    agent.register_tool("example_api", api_config)
    
    # List available tools
    print("Available tools:", agent.list_available_tools())
    
    # Test a simple request (this would fail without a real API key)
    try:
        result = agent.execute_tool_action("example_api", "GET", endpoint="/test")
        print("API result:", result)
    except Exception as e:
        print("API test failed (expected):", e)
    
    # Shutdown
    agent.shutdown()