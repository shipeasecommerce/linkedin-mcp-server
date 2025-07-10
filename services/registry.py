from typing import Dict, List, Optional
from .base import BaseService, ServiceRequest, ServiceResponse

class ServiceRegistry:
    """Registry for managing MCP services"""
    
    def __init__(self):
        self._services: Dict[str, BaseService] = {}
    
    def register_service(self, service: BaseService):
        """Register a new service"""
        self._services[service.name] = service
    
    def unregister_service(self, service_name: str):
        """Unregister a service"""
        if service_name in self._services:
            del self._services[service_name]
    
    def get_service(self, service_name: str) -> Optional[BaseService]:
        """Get a service by name"""
        return self._services.get(service_name)
    
    def list_services(self) -> List[str]:
        """List all registered services"""
        return list(self._services.keys())
    
    def get_all_methods(self) -> Dict[str, List[str]]:
        """Get all available methods for all services"""
        return {
            name: service.get_available_methods() 
            for name, service in self._services.items()
        }
    
    async def handle_request(self, request: ServiceRequest) -> ServiceResponse:
        """Route request to appropriate service"""
        service = self.get_service(request.service_name)
        if not service:
            return ServiceResponse(
                success=False,
                error=f"Service '{request.service_name}' not found"
            )
        
        try:
            return await service.handle_request(request)
        except Exception as e:
            return ServiceResponse(
                success=False,
                error=f"Error in service '{request.service_name}': {str(e)}"
            )