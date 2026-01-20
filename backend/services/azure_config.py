"""
Azure Key Vault service for secure configuration management
"""
import os
import logging
from typing import Optional, Dict, Any
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.core.exceptions import ResourceNotFoundError

logger = logging.getLogger(__name__)


class AzureKeyVaultService:
    """Azure Key Vault service for managing secrets"""
    
    def __init__(self, vault_url: str):
        """
        Initialize Azure Key Vault service
        
        Args:
            vault_url: Key Vault URL
        """
        self.vault_url = vault_url
        
        # Initialize Azure credential
        self.credential = DefaultAzureCredential()
        self.client = SecretClient(vault_url=self.vault_url, credential=self.credential)
        
        logger.info(f"Initialized Azure Key Vault client for: {self.vault_url}")
    
    async def get_secret(self, secret_name: str) -> Optional[str]:
        """
        Get a secret from Azure Key Vault
        
        Args:
            secret_name: Name of the secret to retrieve
            
        Returns:
            Secret value or None if not found
        """
        try:
            secret = self.client.get_secret(secret_name)
            logger.info(f"Successfully retrieved secret: {secret_name}")
            return secret.value
        except ResourceNotFoundError:
            logger.warning(f"Secret not found: {secret_name}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving secret {secret_name}: {str(e)}")
            return None
    
    async def get_multiple_secrets(self, secret_names: list[str]) -> Dict[str, Optional[str]]:
        """
        Get multiple secrets from Azure Key Vault
        
        Args:
            secret_names: List of secret names to retrieve
            
        Returns:
            Dictionary mapping secret names to their values
        """
        secrets = {}
        for secret_name in secret_names:
            secrets[secret_name] = await self.get_secret(secret_name)
        return secrets
    
    async def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """
        Set a secret in Azure Key Vault
        
        Args:
            secret_name: Name of the secret
            secret_value: Value of the secret
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.set_secret(secret_name, secret_value)
            logger.info(f"Successfully set secret: {secret_name}")
            return True
        except Exception as e:
            logger.error(f"Error setting secret {secret_name}: {str(e)}")
            return False


# Global instance
key_vault_service: Optional[AzureKeyVaultService] = None


async def get_key_vault_service() -> AzureKeyVaultService:
    """Get or create the global Key Vault service instance"""
    global key_vault_service
    if key_vault_service is None:
        vault_url = os.getenv("AZURE_KEY_VAULT_URL")
        if not vault_url:
            raise ValueError("KEY_VAULT_URL environment variable is required for Key Vault access")
        key_vault_service = AzureKeyVaultService(vault_url)
    return key_vault_service


async def get_configuration() -> Dict[str, Any]:
    """
    Load configuration from Azure Key Vault and environment variables
    
    Returns:
        Configuration dictionary
    """
    try:
        # Check if we're in development mode (no Key Vault URL provided)
        vault_url = os.getenv("AZURE_KEY_VAULT_URL")
        environment = os.getenv("ENVIRONMENT", "development")
        
        config = {
            # OpenAI Configuration
            "openai_api_key": os.getenv("AZURE_OPENAI_API_KEY"),
            "openai_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", "https://ai-avatar-staging-openai.openai.azure.com/"),
            "openai_api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
            "openai_deployment_name": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4-1"),
            
            # Speech Service Configuration
            "speech_service_key": os.getenv("AZURE_SPEECH_SERVICE_KEY") or os.getenv("SPEECH_KEY"),
            "speech_service_region": os.getenv("AZURE_SPEECH_SERVICE_REGION") or os.getenv("SPEECH_REGION", "eastus"),
            
            # Application Insights
            "appinsights_key": os.getenv("APPINSIGHTS_INSTRUMENTATION_KEY"),
            
            # Environment
            "environment": environment,
            "debug": os.getenv("DEBUG", "false").lower() == "true",
            "use_key_vault": bool(vault_url) and environment != "development",
            "use_mock_ai": os.getenv("USE_MOCK_AI", "false").lower() == "true"
        }
        
        # If in production/staging and Key Vault URL is provided, get additional secrets
        if config["use_key_vault"] and vault_url:
            try:
                vault_service = await get_key_vault_service()
                
                # Define secrets to retrieve
                required_secrets = [
                    "openai-api-key",
                    "speech-service-key", 
                    "appinsights-instrumentation-key"
                ]
                
                # Get secrets from Key Vault (fallback to env vars if not found)
                secrets = await vault_service.get_multiple_secrets(required_secrets)
                
                # Override with Key Vault values if available
                config["openai_api_key"] = secrets.get("openai-api-key") or config["openai_api_key"]
                config["speech_service_key"] = secrets.get("speech-service-key") or config["speech_service_key"]
                config["appinsights_key"] = secrets.get("appinsights-instrumentation-key") or config["appinsights_key"]
                
                logger.info("Configuration loaded from Key Vault")
            except Exception as kv_error:
                logger.warning(f"Key Vault error, using environment variables: {str(kv_error)}")
        
        # Log configuration (without sensitive data)
        logger.info(f"Configuration loaded successfully for environment: {config['environment']}")
        logger.debug(f"OpenAI Endpoint: {config['openai_endpoint']}")
        logger.debug(f"Speech Region: {config['speech_service_region']}")
        logger.debug(f"Using Key Vault: {config['use_key_vault']}")
        
        return config
    
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        raise