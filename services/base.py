from abc import ABC, abstractmethod
from typing import Any, Dict, List
from pydantic import BaseModel

class ServiceRequest(BaseModel):
    service_name: str
    method: str
    parameters: Dict[str, Any] = {}

class ServiceResponse(BaseModel):
    success: bool
    data: Any = None
    error: str = None

class BaseService(ABC):
    """Base class for all MCP services"""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    async def handle_request(self, request: ServiceRequest) -> ServiceResponse:
        """Handle a service request"""
        pass
    
    @abstractmethod
    def get_available_methods(self) -> List[str]:
        """Return list of available methods for this service"""
        pass