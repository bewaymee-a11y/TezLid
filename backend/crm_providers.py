"""
Specific CRM Provider Implementations

AmoCRM, Bitrix24, and other CRM-specific logic.
"""

import logging
from typing import Dict, Any, Optional
import aiohttp
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class AmoCRMProvider:
    """AmoCRM integration provider"""
    
    def __init__(self, config: dict):
        self.domain = config.get("domain", "")
        self.client_id = config.get("client_id", "")
        self.client_secret = config.get("client_secret", "")
        self.access_token = config.get("access_token", "")
        self.refresh_token = config.get("refresh_token", "")
    
    async def create_lead(self, lead_data: dict) -> dict:
        """
        Create lead in AmoCRM
        
        Args:
            lead_data: Lead data from TezLid
            
        Returns:
            AmoCRM lead creation result
        """
        # Map TezLid fields to AmoCRM format
        amocrm_lead = self._map_to_amocrm(lead_data)
        
        url = f"https://{self.domain}/api/v4/leads"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=[amocrm_lead], headers=headers) as response:
                    if response.status == 401:
                        # Token expired, refresh it
                        if await self.refresh_access_token():
                            # Retry with new token
                            return await self.create_lead(lead_data)
                    
                    result = await response.json()
                    
                    if response.status == 200:
                        logger.info(f"Created lead in AmoCRM: {result}")
                        return {"success": True, "data": result}
                    else:
                        logger.error(f"AmoCRM error: {result}")
                        return {"success": False, "error": result}
        
        except Exception as e:
            logger.error(f"Error creating AmoCRM lead: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _map_to_amocrm(self, lead_data: dict) -> dict:
        """Map TezLid lead data to AmoCRM format"""
        # Map lead type to AmoCRM status
        status_map = {
            "hot": 142,      # Example status ID - adjust for your account
            "warm": 143,
            "cold": 144
        }
        
        # Map urgency to AmoCRM tag
        urgency_tags = {
            "high": "Срочно",
            "medium": "Средняя срочность",
            "low": "Не срочно"
        }
        
        amocrm_lead = {
            "name": f"{lead_data.get('service', 'Новый лид')} - {lead_data.get('first_name', 'Клиент')}",
            "price": 0,
            "status_id": status_map.get(lead_data.get("lead_type"), 142),
            "custom_fields_values": [
                {
                    "field_id": 0,  # Replace with actual field ID
                    "values": [{
                        "value": lead_data.get("message", "")
                    }]
                }
            ],
            "_embedded": {
                "tags": [
                    {"name": urgency_tags.get(lead_data.get("urgency"), "")},
                    {"name": f"Telegram ID: {lead_data.get('client_id', '')}"},
                    {"name": "TezLid"}
                ],
                "contacts": [
                    {
                        "name": lead_data.get("first_name", "Клиент"),
                        "custom_fields_values": []
                    }
                ]
            }
        }
        
        # Add username if available
        if lead_data.get("username"):
            amocrm_lead["_embedded"]["contacts"][0]["custom_fields_values"].append({
                "field_id": 0,  # Replace with Telegram field ID
                "values": [{"value": f"@{lead_data['username']}"}]
            })
        
        return amocrm_lead
    
    async def refresh_access_token(self) -> bool:
        """Refresh AmoCRM access token"""
        url = f"https://{self.domain}/oauth2/access_token"
        
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "redirect_uri": "https://example.com/callback"  # Must match registered URI
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    result = await response.json()
                    
                    if response.status == 200:
                        self.access_token = result["access_token"]
                        self.refresh_token = result["refresh_token"]
                        logger.info("AmoCRM token refreshed successfully")
                        
                        # TODO: Save new tokens to database
                        
                        return True
                    else:
                        logger.error(f"Token refresh failed: {result}")
                        return False
        
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            return False


class Bitrix24Provider:
    """Bitrix24 integration provider"""
    
    def __init__(self, config: dict):
        self.webhook_url = config.get("webhook_url", "")
    
    async def create_lead(self, lead_data: dict) -> dict:
        """
        Create lead in Bitrix24
        
        Args:
            lead_data: Lead data from TezLid
            
        Returns:
            Bitrix24 lead creation result
        """
        # Map to Bitrix24 format
        bitrix_lead = self._map_to_bitrix24(lead_data)
        
        url = f"{self.webhook_url}/crm.lead.add.json"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json={"fields": bitrix_lead}) as response:
                    result = await response.json()
                    
                    if result.get("result"):
                        logger.info(f"Created lead in Bitrix24: {result['result']}")
                        return {"success": True, "data": result}
                    else:
                        logger.error(f"Bitrix24 error: {result}")
                        return {"success": False, "error": result.get("error_description")}
        
        except Exception as e:
            logger.error(f"Error creating Bitrix24 lead: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _map_to_bitrix24(self, lead_data: dict) -> dict:
        """Map TezLid lead data to Bitrix24 format"""
        # Map lead type to Bitrix24 source
        source_map = {
            "hot": "TELEGRAM_HOT",
            "warm": "TELEGRAM_WARM",
            "cold": "TELEGRAM_COLD"
        }
        
        bitrix_lead = {
            "TITLE": f"{lead_data.get('service', 'Новый лид')}",
            "NAME": lead_data.get("first_name", "Клиент"),
            "STATUS_ID": "NEW",
            "SOURCE_ID": source_map.get(lead_data.get("lead_type"), "TELEGRAM"),
            "COMMENTS": lead_data.get("message", ""),
            "UF_CRM_TELEGRAM_ID": lead_data.get("client_id", ""),
            "UF_CRM_TELEGRAM_USERNAME": lead_data.get("username", ""),
            "UF_CRM_LEAD_TYPE": lead_data.get("lead_type", ""),
            "UF_CRM_URGENCY": lead_data.get("urgency", ""),
            "UF_CRM_SERVICE": lead_data.get("service", "")
        }
        
        return bitrix_lead


class WebhookProvider:
    """Generic webhook provider for custom integrations"""
    
    def __init__(self, config: dict):
        self.endpoint = config.get("endpoint", "")
        self.method = config.get("method", "POST")
        self.headers = config.get("headers", {})
        self.field_mapping = config.get("field_mapping", {})
    
    async def send_lead(self, lead_data: dict) -> dict:
        """
        Send lead to custom webhook endpoint
        
        Args:
            lead_data: Lead data from TezLid
            
        Returns:
            Webhook response result
        """
        # Apply field mapping
        mapped_data = {}
        for source_field, target_field in self.field_mapping.items():
            if source_field in lead_data:
                mapped_data[target_field] = lead_data[source_field]
        
        # Include unmapped fields
        for key, value in lead_data.items():
            if key not in self.field_mapping:
                mapped_data[key] = value
        
        payload = {
            "event": "lead.created",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": mapped_data
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=self.method,
                    url=self.endpoint,
                    json=payload,
                    headers=self.headers
                ) as response:
                    response_text = await response.text()
                    
                    if 200 <= response.status < 300:
                        logger.info(f"Webhook sent successfully: {response.status}")
                        return {"success": True, "status": response.status, "response": response_text}
                    else:
                        logger.error(f"Webhook failed: {response.status}")
                        return {"success": False, "status": response.status, "error": response_text}
        
        except Exception as e:
            logger.error(f"Error sending webhook: {str(e)}")
            return {"success": False, "error": str(e)}


def get_provider(integration_type: str, config: dict):
    """Factory function to get appropriate CRM provider"""
    providers = {
        "amocrm": AmoCRMProvider,
        "bitrix24": Bitrix24Provider,
        "webhook": WebhookProvider,
        "api": WebhookProvider
    }
    
    provider_class = providers.get(integration_type)
    if provider_class:
        return provider_class(config)
    
    raise ValueError(f"Unknown integration type: {integration_type}")
