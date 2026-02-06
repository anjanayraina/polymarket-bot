from typing import Dict, Any, Type, TypeVar

T = TypeVar("T")

class ServiceLocator:
    def __init__(self):
        self._services: Dict[Type[Any], Any] = {}

    def register(self, service_type: Type[T], instance: T):
        self._services[service_type] = instance

    def get(self, service_type: Type[T]) -> T:
        service = self._services.get(service_type)
        if not service:
            raise ValueError(f"Service {service_type.__name__} not registered.")
        return service

# Global locator instance
service_locator = ServiceLocator()
