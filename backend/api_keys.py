"""
API Key Management Module

Handles generation, validation, and management of API keys for external access.
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

logger = logging.getLogger(__name__)

class APIKeyManager:
    """Manage API keys for external access"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.api_keys
    
    @staticmethod
    def generate_key() -> str:
        """Generate a secure random API key"""
        return f"tlk_{secrets.token_urlsafe(32)}"
    
    @staticmethod
    def hash_key(key: str) -> str:
        """Hash API key for secure storage"""
        return hashlib.sha256(key.encode()).hexdigest()
    
    async def create_key(
        self,
        name: str,
        permissions: List[str] = None,
        rate_limit: int = 1000,
        expires_days: int = 365,
        created_by: str = "system"
    ) -> dict:
        """
        Create a new API key
        
        Args:
            name: Friendly name for the key
            permissions: List of permissions (read, write, delete)
            rate_limit: Requests per hour
            expires_days: Days until expiration
            created_by: User who created the key
            
        Returns:
            dict with key info (includes unhashed key - show only once!)
        """
        if permissions is None:
            permissions = ["read"]
        
        # Generate key
        key = self.generate_key()
        key_hash = self.hash_key(key)
        
        # Calculate expiration
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
        
        # Create key document
        key_doc = {
            "key_hash": key_hash,
            "name": name,
            "permissions": permissions,
            "rate_limit": rate_limit,
            "last_used": None,
            "usage_count": 0,
            "expires_at": expires_at,
            "created_by": created_by,
            "created_at": datetime.now(timezone.utc),
            "enabled": True
        }
        
        # Insert into database
        result = await self.collection.insert_one(key_doc)
        
        logger.info(f"Created API key: {name}")
        
        # Return with unhashed key (only time it will be shown)
        return {
            "id": str(result.inserted_id),
            "key": key,  # Only shown once!
            "name": name,
            "permissions": permissions,
            "rate_limit": rate_limit,
            "expires_at": expires_at.isoformat(),
            "created_at": key_doc["created_at"].isoformat()
        }
    
    async def validate_key(self, key: str) -> Optional[dict]:
        """
        Validate an API key and return its info
        
        Args:
            key: The API key to validate
            
        Returns:
            Key document if valid, None otherwise
        """
        key_hash = self.hash_key(key)
        
        # Find key
        key_doc = await self.collection.find_one({
            "key_hash": key_hash,
            "enabled": True
        })
        
        if not key_doc:
            return None
        
        # Check expiration
        if key_doc["expires_at"] < datetime.now(timezone.utc):
            logger.warning(f"API key expired: {key_doc['name']}")
            return None
        
        # Update usage
        await self.collection.update_one(
            {"_id": key_doc["_id"]},
            {
                "$set": {"last_used": datetime.now(timezone.utc)},
                "$inc": {"usage_count": 1}
            }
        )
        
        return key_doc
    
    async def revoke_key(self, key_hash: str) -> bool:
        """
        Revoke an API key
        
        Args:
            key_hash: Hash of the key to revoke
            
        Returns:
            True if revoked, False if not found
        """
        result = await self.collection.update_one(
            {"key_hash": key_hash},
            {"$set": {"enabled": False}}
        )
        
        if result.modified_count > 0:
            logger.info(f"Revoked API key with hash: {key_hash[:8]}...")
            return True
        
        return False
    
    async def list_keys(self, include_disabled: bool = False) -> List[dict]:
        """
        List all API keys
        
        Args:
            include_disabled: Include disabled keys
            
        Returns:
            List of key documents (without hashes)
        """
        query = {} if include_disabled else {"enabled": True}
        
        cursor = self.collection.find(query, {"key_hash": 0})
        keys = await cursor.to_list(length=100)
        
        # Convert ObjectId to string
        for key in keys:
            key["id"] = str(key.pop("_id"))
            if key.get("created_at"):
                key["created_at"] = key["created_at"].isoformat()
            if key.get("expires_at"):
                key["expires_at"] = key["expires_at"].isoformat()
            if key.get("last_used"):
                key["last_used"] = key["last_used"].isoformat()
        
        return keys
    
    async def check_rate_limit(self, key_doc: dict) -> bool:
        """
        Check if key has exceeded rate limit
        
        Args:
            key_doc: Key document
            
        Returns:
            True if within limit, False if exceeded
        """
        # Simple implementation - can be enhanced with Redis
        rate_limit = key_doc.get("rate_limit", 1000)
        
        # Count requests in last hour
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        
        # For now, just check usage_count (in production, use time-based tracking)
        # This is a simplified version
        return True  # TODO: Implement proper rate limiting with Redis


async def get_api_key_manager(db: AsyncIOMotorDatabase) -> APIKeyManager:
    """Factory function to get API key manager"""
    return APIKeyManager(db)
