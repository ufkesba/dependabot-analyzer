import os
from typing import Optional
from google.cloud import secretmanager
from google.api_core import exceptions

class SecretManager:
    """
    Handles fetching secrets from Google Cloud Secret Manager or environment variables.
    """
    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.client = None

        if self.project_id:
            try:
                self.client = secretmanager.SecretManagerServiceClient()
            except Exception:
                # Fallback to env vars if client initialization fails
                pass

    def get_secret(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get secret from Secret Manager, falling back to environment variable.
        """
        # 1. Try environment variable first (for local development)
        env_val = os.getenv(name)
        if env_val:
            return env_val

        # 2. Try Secret Manager if project_id is set
        if self.client and self.project_id:
            try:
                name_path = f"projects/{self.project_id}/secrets/{name}/versions/latest"
                response = self.client.access_secret_version(request={"name": name_path})
                return response.payload.data.decode("UTF-8")
            except (exceptions.PermissionDenied, exceptions.NotFound):
                # Fallback to default if secret not found or no permission
                pass
            except Exception:
                # Other errors
                pass

        return default

# Global secrets helper
_secrets = None

def get_secret(name: str, default: Optional[str] = None) -> Optional[str]:
    global _secrets
    if _secrets is None:
        _secrets = SecretManager()
    return _secrets.get_secret(name, default)
