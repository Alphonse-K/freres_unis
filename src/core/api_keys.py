# src/core/api_keys.py
from src.core.security import SecurityUtils

class APIKeyUtils:
    @staticmethod
    def generate_key() -> str:
        return SecurityUtils.generate_api_key()

    @staticmethod
    def generate_secret() -> str:
        return SecurityUtils.generate_api_secret()

    @staticmethod
    def hash_secret(secret: str) -> str:
        return SecurityUtils.hash_api_secret(secret)

    @staticmethod
    def verify_secret(plain_secret: str, hashed_secret: str) -> bool:
        return SecurityUtils.verify_api_secret(plain_secret, hashed_secret)
