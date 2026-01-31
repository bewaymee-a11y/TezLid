from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import asyncio
from contextlib import asynccontextmanager
from telegram import Update
from telegram_manager import telegram_manager
from crm_integration import CRMIntegration

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

async def get_crm_integration():
    """Factory to get CRM integration instance with current DB"""
    return CRMIntegration(db, os.environ)

# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: already connected via client initialization
    yield
    # Shutdown: close MongoDB connection
    client.close()

# Create the main app without a prefix
app = FastAPI(lifespan=lifespan)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import telegram bot functions
from telegram_bot import process_message, send_notification_to_manager
from ai_classifier import classify_lead

# Define Models
class Lead(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_id: str  # Multi-tenant: which company owns this lead
    bot_id: Optional[str] = None  # Telegram bot ID for reference
    client_id: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    message: str
    lead_type: str  # "cold", "warm", "hot"
    service: str
    urgency: str  # "low", "medium", "high"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "new"  # "new", "contacted", "converted", "rejected", "accepted"

class TelegramMessage(BaseModel):
    message_id: int
    chat_id: int
    text: str
    username: Optional[str] = None
    first_name: Optional[str] = None

class TelegramWebhook(BaseModel):
    update_id: int
    message: dict

class Company(BaseModel):
    """Multi-tenant company model for BYOB"""
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    bot_token: str
    bot_username: Optional[str] = None
    bot_first_name: Optional[str] = None
    bot_id: Optional[int] = None
    manager_chat_id: int
    webhook_secret: str = Field(default_factory=lambda: __import__('secrets').token_urlsafe(32))
    webhook_url: Optional[str] = None
    status: str = "active"  # "active", "suspended"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ConnectTelegramRequest(BaseModel):
    """Request model for connecting Telegram bot"""
    bot_token: str
    manager_chat_id: int

class ConnectTelegramResponse(BaseModel):
    """Response model for bot connection"""
    success: bool
    company_id: str
    bot_info: Optional[dict] = None
    webhook_url: Optional[str] = None
    message: str

# Add your routes to the router
@api_router.get("/")
async def root():
    return {"message": "Lead Processing Service is running"}

# ========================================
# BYOB Multi-Tenant Endpoints
# ========================================

@api_router.post("/companies", response_model=ConnectTelegramResponse)
async def create_company(
    name: str,
    request: ConnectTelegramRequest
):
    """
    Create new company and connect Telegram bot.
    
    This combines company creation with bot connection in one step.
    """
    try:
        # Verify bot token
        bot_info = await telegram_manager.verify_bot_token(request.bot_token)
        if not bot_info:
            raise HTTPException(status_code=400, detail="Invalid bot token")
        
        # Create company
        company = Company(
            name=name,
            bot_token=request.bot_token,
            bot_username=bot_info.get("username"),
            bot_first_name=bot_info.get("first_name"),
            bot_id=bot_info.get("id"),
            manager_chat_id=request.manager_chat_id
        )
        
        # Get BASE_URL from environment
        base_url = os.environ.get("BASE_URL", "http://localhost:8001")
        webhook_url = f"{base_url}/api/telegram/webhook/{company.id}/{company.webhook_secret}"
        company.webhook_url = webhook_url
        
        # Set webhook
        webhook_set = await telegram_manager.set_webhook(request.bot_token, webhook_url)
        if not webhook_set:
            raise HTTPException(status_code=500, detail="Failed to set webhook")
        
        # Save to database
        company_dict = company.model_dump()
        await db.companies.insert_one(company_dict)
        
        logger.info(f"Company created: {company.id} ({name}) with bot @{company.bot_username}")
        
        return ConnectTelegramResponse(
            success=True,
            company_id=company.id,
            bot_info=bot_info,
            webhook_url=webhook_url,
            message=f"Bot @{company.bot_username} connected successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating company: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/companies/{company_id}/connect-telegram", response_model=ConnectTelegramResponse)
async def connect_telegram_bot(
    company_id: str,
    request: ConnectTelegramRequest
):
    """
    Connect or update Telegram bot for existing company.
    
    - Verifies bot token via Telegram getMe API
    - Generates webhook_secret
    - Sets webhook URL
    - Saves configuration to database
    """
    try:
        # Find company
        company_data = await db.companies.find_one({"id": company_id})
        if not company_data:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Verify bot token
        bot_info = await telegram_manager.verify_bot_token(request.bot_token)
        if not bot_info:
            raise HTTPException(status_code=400, detail="Invalid bot token")
        
        # Update company
        import secrets
        webhook_secret = secrets.token_urlsafe(32)
        base_url = os.environ.get("BASE_URL", "http://localhost:8001")
        webhook_url = f"{base_url}/api/telegram/webhook/{company_id}/{webhook_secret}"
        
        # Set webhook
        webhook_set = await telegram_manager.set_webhook(request.bot_token, webhook_url)
        if not webhook_set:
            raise HTTPException(status_code=500, detail="Failed to set webhook")
        
        # Update database
        await db.companies.update_one(
            {"id": company_id},
            {"$set": {
                "bot_token": request.bot_token,
                "bot_username": bot_info.get("username"),
                "bot_first_name": bot_info.get("first_name"),
                "bot_id": bot_info.get("id"),
                "manager_chat_id": request.manager_chat_id,
                "webhook_secret": webhook_secret,
                "webhook_url": webhook_url,
                "status": "active",
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        logger.info(f"Bot connected for company {company_id}: @{bot_info.get('username')}")
        
        return ConnectTelegramResponse(
            success=True,
            company_id=company_id,
            bot_info=bot_info,
            webhook_url=webhook_url,
            message=f"Bot @{bot_info.get('username')} connected successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting Telegram bot: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/companies/{company_id}")
async def get_company(company_id: str):
    """Get company information (without sensitive data)"""
    company = await db.companies.find_one({"id": company_id}, {"_id": 0, "bot_token": 0, "webhook_secret": 0})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@api_router.delete("/companies/{company_id}/disconnect-telegram")
async def disconnect_telegram_bot(company_id: str):
    """Disconnect Telegram bot and delete webhook"""
    try:
        company = await db.companies.find_one({"id": company_id})
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Delete webhook
        if company.get("bot_token"):
            await telegram_manager.delete_webhook(company["bot_token"])
        
        # Update company status
        await db.companies.update_one(
            {"id": company_id},
            {"$set": {
                "status": "suspended",
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        logger.info(f"Bot disconnected for company {company_id}")
        
        return {"success": True, "message": "Bot disconnected"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting bot: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ========================================
# Legacy Endpoint (deprecated in BYOB mode)
# ========================================


@api_router.post("/telegram/webhook")
async def telegram_webhook(webhook: TelegramWebhook):
    """Receives messages from Telegram bot"""
    try:
        message_data = webhook.message
        
        # Extract message info
        chat_id = message_data.get('chat', {}).get('id')
        text = message_data.get('text', '')
        username = message_data.get('from', {}).get('username')
        first_name = message_data.get('from', {}).get('first_name', 'Клиент')
        
        if not text or not chat_id:
            return {"status": "ignored", "reason": "no text or chat_id"}
        
        logger.info(f"Received message from {username or first_name} (chat_id: {chat_id}): {text}")
        
        # Classify the message using AI
        classification = await classify_lead(text, str(chat_id))
        
        # Save to database if it's a lead
        if classification.get('lead', False):
            lead = Lead(
                client_id=str(chat_id),
                username=username,
                first_name=first_name,
                message=text,
                lead_type=classification.get('lead_type', 'cold'),
                service=classification.get('service', 'Не определено'),
                urgency=classification.get('urgency', 'medium')
            )
            
            # Save to MongoDB
            lead_dict = lead.model_dump()
            lead_dict['timestamp'] = lead_dict['timestamp'].isoformat()
            await db.leads.insert_one(lead_dict)
            
            logger.info(f"Lead saved: {lead.lead_type} - {lead.service} (urgency: {lead.urgency})")
            
            # Send to CRM integrations
            try:
                crm = await get_crm_integration()
                integrations = await crm.list_integrations(enabled_only=True)
                
                for integration in integrations:
                    # Send webhook in background (don't wait for response)
                    asyncio.create_task(
                        crm.send_webhook(
                            integration_id=integration['id'],
                            event="lead.created",
                            lead_data=lead.model_dump(mode='json')
                        )
                    )
                
                logger.info(f"Sent lead to {len(integrations)} CRM integration(s)")
            except Exception as e:
                logger.error(f"Error sending to CRM: {str(e)}")
                # Don't fail the request if CRM integration fails
            
            # Send notification to manager
            await send_notification_to_manager(
                lead_id=lead.id,
                lead_type=lead.lead_type,
                service=lead.service,
                urgency=lead.urgency,
                client_name=first_name or username or "Клиент",
                client_username=f"@{username}" if username else "-",
                message=text,
                chat_id=chat_id
            )
        
        # Send reply to client
        reply = classification.get('reply', 'Спасибо за сообщение! Мы свяжемся с вами в ближайшее время.')
        await process_message(chat_id, reply)
        
        return {"status": "success", "reply_sent": True, "lead_saved": classification.get('lead', False)}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ========================================
# BYOB Multi-Tenant Webhook Endpoint
# ========================================

@api_router.post("/telegram/webhook/{company_id}/{webhook_secret}")
async def telegram_webhook_byob(company_id: str, webhook_secret: str, update_data: dict):
    """
    Multi-tenant webhook endpoint for Telegram updates.
    
    Handles both messages (lead creation) and callback_queries (manager actions).
    Each company has their own webhook URL with secret for security.
    """
    try:
        # Validate company and webhook secret
        company = await db.companies.find_one({"id": company_id})
        if not company:
            logger.warning(f"Webhook called for unknown company: {company_id}")
            raise HTTPException(status_code=404, detail="Company not found")
        
        if company.get("webhook_secret") != webhook_secret:
            logger.warning(f"Invalid webhook secret for company: {company_id}")
            raise HTTPException(status_code=403, detail="Invalid webhook secret")
        
        if company.get("status") != "active":
            logger.warning(f"Webhook called for inactive company: {company_id}")
            return {"status": "ignored", "reason": "company not active"}
        
        # Get company's bot token
        bot_token = company.get("bot_token")
        manager_chat_id = company.get("manager_chat_id")
        
        if not bot_token:
            raise HTTPException(status_code=500, detail="Bot token not configured")
        
        # Parse Telegram update
        update = Update.de_json(update_data, telegram_manager.get_bot(bot_token))
        
        # Handle message (lead creation)
        if update.message and update.message.text:
            message = update.message
            chat_id = message.chat_id
            text = message.text
            username = message.from_user.username if message.from_user else None
            first_name = message.from_user.first_name if message.from_user else "Клиент"
            
            logger.info(f"[{company_id}] Received message from {username or first_name}: {text}")
            
            # Classify the message using AI
            classification = await classify_lead(text, str(chat_id))
            
            # Save to database if it's a lead
            if classification.get('lead', False):
                lead = Lead(
                    company_id=company_id,
                    bot_id=str(company.get("bot_id")),
                    client_id=str(chat_id),
                    username=username,
                    first_name=first_name,
                    message=text,
                    lead_type=classification.get('lead_type', 'cold'),
                    service=classification.get('service', 'Не определено'),
                    urgency=classification.get('urgency', 'medium')
                )
                
                # Save to MongoDB
                lead_dict = lead.model_dump()
                lead_dict['timestamp'] = lead_dict['timestamp'].isoformat()
                await db.leads.insert_one(lead_dict)
                
                logger.info(f"[{company_id}] Lead created: {lead.id}")
                
                # Send notification to manager using company's bot
                await telegram_manager.send_manager_notification(
                    bot_token=bot_token,
                    manager_chat_id=manager_chat_id,
                    lead_id=lead.id,
                    lead_type=lead.lead_type,
                    service=lead.service,
                    urgency=lead.urgency,
                    client_name=first_name or username or "Клиент",
                    client_username=f"@{username}" if username else "-",
                    message=text,
                    chat_id=chat_id
                )
            
                # Send to CRM integrations
                try:
                    crm = await get_crm_integration()
                    integrations = await crm.list_integrations(enabled_only=True)
                    
                    for integration in integrations:
                        # Send webhook in background (don't wait for response)
                        asyncio.create_task(
                            crm.send_webhook(
                                integration_id=integration['id'],
                                event="lead.created",
                                lead_data=lead.model_dump(mode='json')
                            )
                        )
                    
                    logger.info(f"[{company_id}] Sent lead to {len(integrations)} CRM integration(s)")
                except Exception as e:
                    logger.error(f"Error sending to CRM: {str(e)}")
                    # Don't fail the request if CRM integration fails
            
            # Send reply to client using company's bot
            reply = classification.get('reply', 'Спасибо за сообщение! Мы свяжемся с вами в ближайшее время.')
            await telegram_manager.send_message(
                bot_token=bot_token,
                chat_id=chat_id,
                text=reply
            )
            
            return {"status": "success", "lead_saved": classification.get('lead', False)}
        
        # Handle callback_query (manager actions)
        elif update.callback_query:
            query = update.callback_query
            callback_data = query.data
            
            logger.info(f"[{company_id}] Received callback: {callback_data}")
            
            # Parse callback_data: lead:{lead_id}:{action}
            parts = callback_data.split(":")
            if len(parts) != 3 or parts[0] != "lead":
                await telegram_manager.answer_callback_query(
                    bot_token=bot_token,
                    callback_query_id=query.id,
                    text="❌ Неверный формат команды",
                    show_alert=True
                )
                return {"status": "error", "reason": "invalid callback format"}
            
            _, lead_id, action = parts
            
            # Validate action
            if action not in ["accept", "call", "reject"]:
                await telegram_manager.answer_callback_query(
                    bot_token=bot_token,
                    callback_query_id=query.id,
                    text="❌ Неверное действие",
                    show_alert=True
                )
                return {"status": "error", "reason": "invalid action"}
            
            # Get lead from database
            lead = await db.leads.find_one({"id": lead_id, "company_id": company_id})
            if not lead:
                await telegram_manager.answer_callback_query(
                    bot_token=bot_token,
                    callback_query_id=query.id,
                    text="❌ Лид не найден",
                    show_alert=True
                )
                return {"status": "error", "reason": "lead not found"}
            
            # Map action to status
            status_map = {
                "accept": "accepted",
                "call": "contacted",
                "reject": "rejected"
            }
            new_status = status_map[action]
            
            # Update lead status
            await db.leads.update_one(
                {"id": lead_id},
                {"$set": {"status": new_status}}
            )
            
            logger.info(f"[{company_id}] Lead {lead_id} status updated to {new_status}")
            
            # Send message to client
            client_messages = {
                "accept": "✅ Заявка принята! Менеджер скоро свяжется с вами.",
                "call": "📞 Менеджер сейчас свяжется с вами по телефону.",
                "reject": "❌ Сейчас не можем помочь. Если актуально — напишите позже."
            }
            
            await telegram_manager.send_message(
                bot_token=bot_token,
                chat_id=int(lead["client_id"]),
                text=client_messages[action]
            )
            
            # Edit manager's message (remove buttons)
            action_names = {
                "accept": "✅ Заявка принята",
                "call": "📞 Звонок запланирован",
                "reject": "❌ Заявка отклонена"
            }
            
            new_text = f"{query.message.text}\n\n━━━━━━━━━━━━━━━━\n{action_names[action]}\n⏰ {datetime.now().strftime('%H:%M:%S')}"
            
            # First remove buttons explicitly
            await telegram_manager.edit_message_reply_markup(
                bot_token=bot_token,
                chat_id=query.message.chat_id,
                message_id=query.message.message_id,
                reply_markup=None
            )
            
            # Then edit text
            await telegram_manager.edit_message_text(
                bot_token=bot_token,
                chat_id=query.message.chat_id,
                message_id=query.message.message_id,
                text=new_text
            )
            
            # Answer callback query
            await telegram_manager.answer_callback_query(
                bot_token=bot_token,
                callback_query_id=query.id,
                text=f"{action_names[action]} ✓",
                show_alert=True
            )
            
            return {"status": "success", "action": action, "new_status": new_status}
        
        else:
            return {"status": "ignored", "reason": "no message or callback_query"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing BYOB webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/leads", response_model=List[Lead])
async def get_leads(
    company_id: Optional[str] = None,  # BYOB: filter by company
    status: Optional[str] = None,
    urgency: Optional[str] = None,
    lead_type: Optional[str] = None,
    limit: int = 100
):
    """Get all leads with optional filters"""
    try:
        # Build query
        query = {}
        if company_id:  # BYOB: filter by company
            query['company_id'] = company_id
        if status:
            query['status'] = status
        if urgency:
            query['urgency'] = urgency
        if lead_type:
            query['lead_type'] = lead_type
        
        # Fetch from database
        leads = await db.leads.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)
        
        # Convert ISO string timestamps back to datetime objects
        for lead in leads:
            if isinstance(lead['timestamp'], str):
                lead['timestamp'] = datetime.fromisoformat(lead['timestamp'])
        
        return leads
    except Exception as e:
        logger.error(f"Error fetching leads: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/leads/{lead_id}")
async def get_lead(lead_id: str):
    """Get a single lead by ID"""
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if isinstance(lead['timestamp'], str):
        lead['timestamp'] = datetime.fromisoformat(lead['timestamp'])
    
    return lead

@api_router.put("/leads/{lead_id}/status")
async def update_lead_status(lead_id: str, status: str):
    """Update lead status"""
    result = await db.leads.update_one(
        {"id": lead_id},
        {"$set": {"status": status}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return {"success": True, "message": "Status updated"}

class ManagerActionRequest(BaseModel):
    action: str  # "accept", "call", "reject"

@api_router.post("/leads/{lead_id}/manager-action")
async def manager_action(lead_id: str, request: ManagerActionRequest):
    """
    Handle manager action on a lead (from Telegram inline buttons)
    
    Args:
        lead_id: Lead identifier
        request: Contains action type (accept/call/reject)
    
    Returns:
        Success status and updated lead information
    """
    try:
        # Get lead from database
        lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        # Map action to status
        status_map = {
            "accept": "accepted",
            "call": "contacted",
            "reject": "rejected"
        }
        
        new_status = status_map.get(request.action)
        if not new_status:
            raise HTTPException(status_code=400, detail=f"Invalid action: {request.action}")
        
        # Update lead status in database
        await db.leads.update_one(
            {"id": lead_id},
            {"$set": {"status": new_status}}
        )
        
        logger.info(f"Lead {lead_id} status updated to {new_status} by manager action")
        
        # Get client chat ID
        client_chat_id = int(lead.get('client_id'))
        
        # Send appropriate message to client
        client_messages = {
            "accept": "✅ Заявка принята! Менеджер скоро свяжется с вами.",
            "call": "📞 Менеджер сейчас свяжется с вами по телефону.",
            "reject": "❌ Сейчас не можем помочь. Если актуально — напишите позже."
        }
        
        client_message = client_messages.get(request.action, "Спасибо за ваше обращение!")
        
        # Send message to client
        await process_message(client_chat_id, client_message)
        
        logger.info(f"Client notification sent for lead {lead_id}, action: {request.action}")
        
        return {
            "success": True,
            "lead_id": lead_id,
            "new_status": new_status,
            "action": request.action,
            "client_notified": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing manager action: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/stats")
async def get_stats():
    """Get lead statistics"""
    try:
        total = await db.leads.count_documents({})
        hot_leads = await db.leads.count_documents({"lead_type": "hot"})
        warm_leads = await db.leads.count_documents({"lead_type": "warm"})
        cold_leads = await db.leads.count_documents({"lead_type": "cold"})
        
        high_urgency = await db.leads.count_documents({"urgency": "high"})
        new_leads = await db.leads.count_documents({"status": "new"})
        
        return {
            "total": total,
            "by_type": {
                "hot": hot_leads,
                "warm": warm_leads,
                "cold": cold_leads
            },
            "high_urgency": high_urgency,
            "new_leads": new_leads
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# CRM Integration Endpoints
# ============================================================================

from api_keys import APIKeyManager
from crm_integration import CRMIntegration
from crm_providers import get_provider
from fastapi import Header, Depends

# Initialize CRM integration
crm_config = {
    "CRM_WEBHOOK_SECRET": os.environ.get("CRM_WEBHOOK_SECRET", ""),
    "CRM_RETRY_ATTEMPTS": os.environ.get("CRM_RETRY_ATTEMPTS", "3"),
    "CRM_TIMEOUT": os.environ.get("CRM_TIMEOUT", "30")
}

async def get_crm_integration():
    """Dependency to get CRM integration instance"""
    return CRMIntegration(db, crm_config)

async def get_api_key_manager():
    """Dependency to get API key manager instance"""
    return APIKeyManager(db)

async def verify_api_key(authorization: str = Header(None)):
    """Verify API key from Authorization header"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing API key")
    
    # Extract key from "Bearer {key}" format
    try:
        scheme, key = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    # Validate key
    api_key_manager = await get_api_key_manager()
    key_doc = await api_key_manager.validate_key(key)
    
    if not key_doc:
        raise HTTPException(status_code=401, detail="Invalid or expired API key")
    
    return key_doc

# CRM Integrations Management
@api_router.post("/crm/integrations")
async def create_crm_integration(
    name: str,
    integration_type: str,
    config: dict,
    events: list = None,
    crm: CRMIntegration = Depends(get_crm_integration)
):
    """Create a new CRM integration"""
    try:
        integration = await crm.create_integration(name, integration_type, config, events)
        return {"success": True, "integration": integration}
    except Exception as e:
        logger.error(f"Error creating integration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/crm/integrations")
async def list_crm_integrations(
    enabled_only: bool = True,
    crm: CRMIntegration = Depends(get_crm_integration)
):
    """List all CRM integrations"""
    integrations = await crm.list_integrations(enabled_only)
    return {"integrations": integrations}

@api_router.get("/crm/integrations/{integration_id}")
async def get_crm_integration_endpoint(
    integration_id: str,
    crm: CRMIntegration = Depends(get_crm_integration)
):
    """Get specific CRM integration"""
    integration = await crm.get_integration(integration_id)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    return integration

@api_router.put("/crm/integrations/{integration_id}")
async def update_crm_integration(
    integration_id: str,
    updates: dict,
    crm: CRMIntegration = Depends(get_crm_integration)
):
    """Update CRM integration"""
    success = await crm.update_integration(integration_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Integration not found")
    return {"success": True}

@api_router.delete("/crm/integrations/{integration_id}")
async def delete_crm_integration(
    integration_id: str,
    crm: CRMIntegration = Depends(get_crm_integration)
):
    """Delete CRM integration"""
    success = await crm.delete_integration(integration_id)
    if not success:
        raise HTTPException(status_code=404, detail="Integration not found")
    return {"success": True}

# Webhook Logs
@api_router.get("/crm/webhooks/logs")
async def get_webhook_logs(
    integration_id: str = None,
    limit: int = 100,
    crm: CRMIntegration = Depends(get_crm_integration)
):
    """Get webhook delivery logs"""
    logs = await crm.get_webhook_logs(integration_id, limit)
    return {"logs": logs}

# Test webhook delivery
@api_router.post("/crm/integrations/{integration_id}/test")
async def test_crm_integration(
    integration_id: str,
    crm: CRMIntegration = Depends(get_crm_integration)
):
    """Test CRM integration with sample data"""
    # Create test lead data
    test_lead = {
        "id": "test_lead_123",
        "client_id": "123456789",
        "username": "test_user",
        "first_name": "Test User",
        "message": "This is a test lead from TezLid",
        "lead_type": "warm",
        "service": "Test Service",
        "urgency": "medium",
        "status": "new"
    }
    
    result = await crm.send_webhook(integration_id, "lead.created", test_lead)
    return result

# API Keys Management
@api_router.post("/api-keys")
async def create_api_key(
    name: str,
    permissions: list = None,
    rate_limit: int = 1000,
    expires_days: int = 365,
    api_key_manager: APIKeyManager = Depends(get_api_key_manager)
):
    """Create a new API key"""
    key_info = await api_key_manager.create_key(name, permissions, rate_limit, expires_days)
    return key_info

@api_router.get("/api-keys")
async def list_api_keys(
    include_disabled: bool = False,
    api_key_manager: APIKeyManager = Depends(get_api_key_manager)
):
    """List all API keys"""
    keys = await api_key_manager.list_keys(include_disabled)
    return {"keys": keys}

@api_router.delete("/api-keys/{key_hash}")
async def revoke_api_key(
    key_hash: str,
    api_key_manager: APIKeyManager = Depends(get_api_key_manager)
):
    """Revoke an API key"""
    success = await api_key_manager.revoke_key(key_hash)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"success": True}

# ============================================================================
# External API Endpoints (Require API Key)
# ============================================================================

@api_router.get("/external/leads", dependencies=[Depends(verify_api_key)])
async def external_get_leads(
    status: Optional[str] = None,
    urgency: Optional[str] = None,
    lead_type: Optional[str] = None,
    limit: int = 100
):
    """External API: Get all leads"""
    # Reuse existing leads endpoint logic
    query = {}
    if status:
        query['status'] = status
    if urgency:
        query['urgency'] = urgency
    if lead_type:
        query['lead_type'] = lead_type
    
    leads = await db.leads.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    
    for lead in leads:
        if isinstance(lead['timestamp'], str):
            lead['timestamp'] = datetime.fromisoformat(lead['timestamp'])
    
    return {"leads": leads}

@api_router.get("/external/leads/{lead_id}", dependencies=[Depends(verify_api_key)])
async def external_get_lead(lead_id: str):
    """External API: Get specific lead"""
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if isinstance(lead['timestamp'], str):
        lead['timestamp'] = datetime.fromisoformat(lead['timestamp'])
    
    return lead

@api_router.post("/external/leads", dependencies=[Depends(verify_api_key)])
async def external_create_lead(lead: Lead):
    """External API: Create a new lead"""
    lead_dict = lead.model_dump()
    lead_dict['timestamp'] = lead_dict['timestamp'].isoformat()
    await db.leads.insert_one(lead_dict)
    
    logger.info(f"Lead created via API: {lead.id}")
    
    return {"success": True, "lead_id": lead.id}

@api_router.put("/external/leads/{lead_id}", dependencies=[Depends(verify_api_key)])
async def external_update_lead(lead_id: str, updates: dict):
    """External API: Update a lead"""
    result = await db.leads.update_one(
        {"id": lead_id},
        {"$set": updates}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return {"success": True}

# ============================================================================
# Incoming Webhooks from CRM
# ============================================================================

@api_router.post("/crm/webhook/amocrm")
async def amocrm_webhook(data: dict):
    """Receive webhook from AmoCRM"""
    logger.info(f"Received AmoCRM webhook: {data}")
    
    # TODO: Process AmoCRM webhook
    # Update lead status, add notes, etc.
    
    return {"status": "received"}

@api_router.post("/crm/webhook/bitrix24")
async def bitrix24_webhook(data: dict):
    """Receive webhook from Bitrix24"""
    logger.info(f"Received Bitrix24 webhook: {data}")
    
    # TODO: Process Bitrix24 webhook
    
    return {"status": "received"}

@api_router.post("/crm/webhook/custom")
async def custom_webhook(data: dict):
    """Receive custom webhook"""
    logger.info(f"Received custom webhook: {data}")
    
    # TODO: Process custom webhook
    
    return {"status": "received"}

# Include the router in the main app
app.include_router(api_router)


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)