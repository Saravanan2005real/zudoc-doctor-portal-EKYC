from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class VerificationProvider(ABC):
    """
    Base interface for all verification execution providers.
    Every provider (e.g. AWS Rekognition, Azure Face, Custom API) 
    must implement this interface.
    """
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the unique identifier for this provider."""
        pass

    @abstractmethod
    def execute(self, application_context: Dict[str, Any], step_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the verification logic.
        
        :param application_context: Data related to the application (images, details, previous step results).
        :param step_config: Specific configuration for this step (e.g., threshold values).
        :return: A dictionary containing the standard verification result schema.
        """
        pass
