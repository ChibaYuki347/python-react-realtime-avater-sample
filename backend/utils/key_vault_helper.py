"""
Azure Key Vault統合ヘルパー
環境変数からKey Vault参照を解析して、実際のシークレット値を取得
"""
import os
import re
import logging
from typing import Optional
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

logger = logging.getLogger(__name__)


class KeyVaultHelper:
    """Key Vaultからシークレットを取得するヘルパークラス"""
    
    _instance: Optional['KeyVaultHelper'] = None
    _secret_client: Optional[SecretClient] = None
    
    @classmethod
    def get_instance(cls) -> 'KeyVaultHelper':
        """シングルトンインスタンスを取得"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self.key_vault_url = os.getenv("AZURE_KEY_VAULT_URL")
        self.use_managed_identity = os.getenv("USE_MANAGED_IDENTITY", "false").lower() == "true"
        
    def get_secret(self, secret_name: str) -> Optional[str]:
        """
        Key Vaultからシークレットを取得
        
        Args:
            secret_name: シークレット名
            
        Returns:
            シークレット値、またはKey Vaultが未設定の場合はNone
        """
        if not self.key_vault_url or not self.use_managed_identity:
            logger.debug(f"Key Vault not configured for secret: {secret_name}")
            return None
        
        try:
            if self._secret_client is None:
                credential = DefaultAzureCredential()
                self._secret_client = SecretClient(
                    vault_url=self.key_vault_url,
                    credential=credential
                )
            
            secret = self._secret_client.get_secret(secret_name)
            logger.info(f"Successfully retrieved secret: {secret_name}")
            return secret.value
            
        except Exception as e:
            logger.error(f"Failed to get secret from Key Vault: {e}")
            return None
    
    @staticmethod
    def resolve_env_value(value: str) -> str:
        """
        環境変数値をパース（Key Vault参照または直接値）
        
        形式: ${KEY_VAULT_SECRET:secret-name} または 直接値
        
        Args:
            value: 解析する値
            
        Returns:
            実際の値
        """
        if not value:
            return value
        
        # Key Vault参照パターンをチェック
        pattern = r'\$\{KEY_VAULT_SECRET:([^}]+)\}'
        match = re.match(pattern, value)
        
        if match:
            secret_name = match.group(1)
            helper = KeyVaultHelper.get_instance()
            secret_value = helper.get_secret(secret_name)
            
            if secret_value:
                logger.info(f"Resolved Key Vault secret: {secret_name}")
                return secret_value
            else:
                logger.warning(f"Could not resolve Key Vault secret: {secret_name}, using original value")
                return value
        
        return value
