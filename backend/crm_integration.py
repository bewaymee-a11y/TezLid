"""
CRM Integration Module

Core functionality for integrating with external CRM systems.
Handles webhook delivery, field mapping, and error handling.
"""

import aiohttp
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

class CRMIntegration:
    """Base class for CRM integrations"""
    
    def __init__(self, db: AsyncIOMotorDatabase, config: dict):
        self.db = db
        self.config = config
        self.integrations_collection = db.crm_integrations
        self.logs_collection = db.webhook_logs
    
    async def send_webhook(
        self,
        integration_id: str,
        event: str,
        lead_data: dict,
        retry_count: int = 0
    ) -> dict:
        """
        Send webhook to CRM system
        
        Args:
            integration_id: CRM integration ID
            event: Event type (lead.created, lead.updated, etc.)
            lead_data: Lead data to send
            retry_count: Current retry attempt
            
        Returns:
            Result dict with status and response
        """
        # Get integration config
        integration = await self.integrations_collection.find_one({"id": integration_id})
        
        if not integration or not integration.get("enabled"):
            logger.warning(f"Integration {integration_id} not found or disabled")
            return {"status": "failed", "error": "Integration not enabled"}
        
        # Check if event is enabled for this integration
        if event not in integration.get("events", []):
            logger.debug(f"Event {event} not enabled for integration {integration_id}")
            return {"status": "skipped", "reason": "Event not enabled"}
        
        # Prepare payload
        payload = {
            "event": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "lead": self._map_fields(lead_data, integration.get("config", {}).get("field_mapping", {}))
        }
        
        # Get webhook URL
        webhook_url = self._get_webhook_url(integration)
        
        if not webhook_url:
            logger.error(f"No webhook URL configured for integration {integration_id}")
            return {"status": "failed", "error": "No webhook URL"}
        
        # Send request
        try:
            result = await self._send_http_request(
                url=webhook_url,
                method=integration.get("config", {}).get("method", "POST"),
                payload=payload,
                headers=self._get_headers(integration),
                timeout=int(self.config.get("CRM_TIMEOUT", 30))
            )
            
            # Log webhook
            await self._log_webhook(
                integration_id=integration_id,
                event=event,
                lead_id=lead_data.get("id"),
                status="success" if result["success"] else "failed",
                request=payload,
                response=result.get("response"),
                error=result.get("error")
            )
            
            # Update last sync time
            await self.integrations_collection.update_one(
                {"id": integration_id},
                {"$set": {"last_sync": datetime.now(timezone.utc)}}
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending webhook: {str(e)}")
            
            # Retry logic
            max_retries = int(self.config.get("CRM_RETRY_ATTEMPTS", 3))
            if retry_count < max_retries:
                logger.info(f"Retrying webhook (attempt {retry_count + 1}/{max_retries})")
                return await self.send_webhook(integration_id, event, lead_data, retry_count + 1)
            
            # Log failed webhook
            await self._log_webhook(
                integration_id=integration_id,
                event=event,
                lead_id=lead_data.get("id"),
                status="failed",
                request=payload,
                response=None,
                error=str(e)
            )
            
            return {"status": "failed", "error": str(e)}
    
    async def _send_http_request(
        self,
        url: str,
        method: str,
        payload: dict,
        headers: dict,
        timeout: int
    ) -> dict:
        """Send HTTP request to webhook URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    response_text = await response.text()
                    
                    return {
                        "success": 200 <= response.status < 300,
                        "status_code": response.status,
                        "response": response_text
                    }
        except aiohttp.ClientError as e:
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_webhook_url(self, integration: dict) -> Optional[str]:
        """Get webhook URL based on integration type"""
        integration_type = integration.get("type")
        config = integration.get("config", {})
        
        if integration_type == "amocrm":
            # AmoCRM uses API endpoint
            domain = config.get("domain", "")
            return f"https://{domain}/api/v4/leads"
        
        elif integration_type == "bitrix24":
            # Bitrix24 webhook
            return config.get("webhook_url")
        
        elif integration_type in ["webhook", "api"]:
            # Custom webhook
            return config.get("endpoint")
        
        return None
    
    def _get_headers(self, integration: dict) -> dict:
        """Get headers for webhook request"""
        config = integration.get("config", {})
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "TezLid-CRM-Integration/1.0"
        }
        
        # Add custom headers
        if "headers" in config:
            headers.update(config["headers"])
        
        # Add authorization for AmoCRM
        if integration.get("type") == "amocrm" and config.get("access_token"):
            headers["Authorization"] = f"Bearer {config['access_token']}"
        
        # Add HMAC signature if secret is configured
        if self.config.get("CRM_WEBHOOK_SECRET"):
            # TODO: Implement HMAC signature
            pass
        
        return headers
    
    def _map_fields(self, data: dict, field_mapping: dict) -> dict:
        """Map fields according to configuration"""
        if not field_mapping:
            return data
        
        mapped_data = {}
        for source_field, target_field in field_mapping.items():
            if source_field in data:
                mapped_data[target_field] = data[source_field]
        
        # Include unmapped fields
        for key, value in data.items():
            if key not in field_mapping:
                mapped_data[key] = value
        
        return mapped_data
    
    async def _log_webhook(
        self,
        integration_id: str,
        event: str,
        lead_id: str,
        status: str,
        request: dict,
        response: Any,
        error: Optional[str] = None
    ):
        """Log webhook delivery attempt"""
        log_entry = {
            "integration_id": integration_id,
            "event": event,
            "lead_id": lead_id,
            "status": status,
            "request": request,
            "response": response,
            "error": error,
            "timestamp": datetime.now(timezone.utc)
        }
        
        await self.logs_collection.insert_one(log_entry)
    
    async def get_integration(self, integration_id: str) -> Optional[dict]:
        """Get integration by ID"""
        integration = await self.integrations_collection.find_one({"id": integration_id})
        
        if integration:
            integration["_id"] = str(integration["_id"])
        
        return integration
    
    async def list_integrations(self, enabled_only: bool = True) -> List[dict]:
        """List all CRM integrations"""
        query = {"enabled": True} if enabled_only else {}
        cursor = self.integrations_collection.find(query)
        integrations = await cursor.to_list(length=100)
        
        for integration in integrations:
            integration["_id"] = str(integration["_id"])
        
        return integrations
    
    async def create_integration(
        self,
        name: str,
        integration_type: str,
        config: dict,
        events: List[str] = None
    ) -> dict:
        """Create new CRM integration"""
        if events is None:
            events = ["lead.created", "lead.updated"]
        
        integration = {
            "id": f"crm_{int(datetime.now().timestamp())}",
            "name": name,
            "type": integration_type,
            "enabled": True,
            "config": config,
            "events": events,
            "created_at": datetime.now(timezone.utc),
            "last_sync": None
        }
        
        await self.integrations_collection.insert_one(integration)
        logger.info(f"Created CRM integration: {name} ({integration_type})")
        
        return integration
    
    async def update_integration(self, integration_id: str, updates: dict) -> bool:
        """Update CRM integration"""
        result = await self.integrations_collection.update_one(
            {"id": integration_id},
            {"$set": updates}
        )
        
        return result.modified_count > 0
    
    async def delete_integration(self, integration_id: str) -> bool:
        """Delete CRM integration"""
        result = await self.integrations_collection.delete_one({"id": integration_id})
        return result.deleted_count > 0
    
    async def get_webhook_logs(
        self,
        integration_id: Optional[str] = None,
        limit: int = 100
    ) -> List[dict]:
        """Get webhook delivery logs"""
        query = {}
        if integration_id:
            query["integration_id"] = integration_id
        
        cursor = self.logs_collection.find(query).sort("timestamp", -1).limit(limit)
        logs = await cursor.to_list(length=limit)
        
        for log in logs:
            log["_id"] = str(log["_id"])
            if log.get("timestamp"):
                log["timestamp"] = log["timestamp"].isoformat()
        
        return logs


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC signature of incoming webhook"""
    expected_signature = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)
