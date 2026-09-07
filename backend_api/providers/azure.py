from providers.base import VerificationProvider
from typing import Dict, Any
import random

class AzureFaceProvider(VerificationProvider):
    
    @property
    def provider_name(self) -> str:
        return "azure_face"
        
    def execute(self, application_context: Dict[str, Any], step_config: Dict[str, Any]) -> Dict[str, Any]:
        # Mock Azure Face API call
        threshold = step_config.get("threshold", 0.85)
        
        confidence = random.uniform(0.60, 0.99)
        status = "PASSED" if confidence >= threshold else "FAILED"
        
        return {
            "status": status,
            "confidence": round(confidence, 4),
            "provider": self.provider_name,
            "metadata": {
                "azure_req_id": f"azure_{random.randint(1000,9999)}",
                "similarity": confidence
            }
        }
