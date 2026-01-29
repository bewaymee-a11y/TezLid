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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

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
    client_id: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    message: str
    lead_type: str  # "cold", "warm", "hot"
    service: str
    urgency: str  # "low", "medium", "high"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "new"  # "new", "contacted", "converted", "rejected"

class TelegramMessage(BaseModel):
    message_id: int
    chat_id: int
    text: str
    username: Optional[str] = None
    first_name: Optional[str] = None

class TelegramWebhook(BaseModel):
    update_id: int
    message: dict

# Add your routes to the router
@api_router.get("/")
async def root():
    return {"message": "Lead Processing Service is running"}

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
            
            # Send notification to manager
            await send_notification_to_manager(
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

@api_router.get("/leads", response_model=List[Lead])
async def get_leads(
    status: Optional[str] = None,
    urgency: Optional[str] = None,
    lead_type: Optional[str] = None,
    limit: int = 100
):
    """Get all leads with optional filters"""
    try:
        # Build query
        query = {}
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

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)