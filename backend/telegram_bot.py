import os
import logging
from telegram import Bot
from telegram.error import TelegramError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Initialize bot
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
MANAGER_CHAT_ID = os.environ.get('MANAGER_CHAT_ID', '')

bot = None
if BOT_TOKEN and BOT_TOKEN != 'your_bot_token_here':
    bot = Bot(token=BOT_TOKEN)
else:
    logger.warning("Telegram bot token not configured")

async def process_message(chat_id: int, text: str):
    """
    Send a message to a user via Telegram
    
    Args:
        chat_id: Telegram chat ID
        text: Message text to send
    """
    if not bot:
        logger.warning("Bot not initialized, skipping message send")
        return False
    
    try:
        await bot.send_message(chat_id=chat_id, text=text)
        logger.info(f"Message sent to chat_id {chat_id}")
        return True
    except TelegramError as e:
        logger.error(f"Failed to send message to {chat_id}: {str(e)}")
        return False

async def send_notification_to_manager(
    lead_type: str,
    service: str,
    urgency: str,
    client_name: str,
    client_username: str,
    message: str,
    chat_id: int
):
    """
    Send notification about new lead to manager
    
    Args:
        lead_type: Type of lead (hot/warm/cold)
        service: Service requested
        urgency: Urgency level
        client_name: Client's name
        client_username: Client's username
        message: Original message
        chat_id: Client's chat ID
    """
    if not bot:
        logger.warning("Bot not initialized, skipping manager notification")
        return False
    
    if not MANAGER_CHAT_ID or MANAGER_CHAT_ID == 'your_manager_chat_id_here':
        logger.warning("Manager chat ID not configured")
        return False
    
    # Format notification
    urgency_emoji = {
        "high": "🔥",
        "medium": "⚡",
        "low": "📝"
    }
    
    lead_emoji = {
        "hot": "🔥 ГОРЯЧИЙ ЛИД",
        "warm": "⚡ ТЁПЛЫЙ ЛИД",
        "cold": "❄️ ХОЛОДНЫЙ ЛИД"
    }
    
    notification = f"""{lead_emoji.get(lead_type, lead_type.upper())}

{urgency_emoji.get(urgency, '')} Срочность: {urgency.upper()}
📋 Услуга: {service}

👤 Клиент: {client_name}
✉️ Username: {client_username}
💬 ID чата: {chat_id}

📝 Сообщение:
{message}

⏰ Время: {os.popen('date +"%Y-%m-%d %H:%M:%S"').read().strip()}"""
    
    try:
        await bot.send_message(chat_id=MANAGER_CHAT_ID, text=notification)
        logger.info(f"Notification sent to manager about {lead_type} lead")
        return True
    except TelegramError as e:
        logger.error(f"Failed to send notification to manager: {str(e)}")
        return False

async def get_bot_info():
    """
    Get bot information
    """
    if not bot:
        return None
    
    try:
        me = await bot.get_me()
        return {
            "id": me.id,
            "username": me.username,
            "first_name": me.first_name
        }
    except TelegramError as e:
        logger.error(f"Failed to get bot info: {str(e)}")
        return None