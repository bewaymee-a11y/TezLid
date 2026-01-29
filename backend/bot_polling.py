#!/usr/bin/env python3
"""
Telegram Bot Polling Script

This script runs the Telegram bot in polling mode to receive messages.
Run this separately from the main FastAPI server.

Usage:
    python bot_polling.py
"""

import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
BACKEND_URL = os.environ.get('BACKEND_URL', 'http://localhost:8001')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle incoming messages and forward to backend
    """
    if not update.message or not update.message.text:
        return
    
    # Prepare webhook data
    webhook_data = {
        "update_id": update.update_id,
        "message": {
            "message_id": update.message.message_id,
            "text": update.message.text,
            "chat": {
                "id": update.message.chat.id
            },
            "from": {
                "id": update.message.from_user.id,
                "username": update.message.from_user.username,
                "first_name": update.message.from_user.first_name
            }
        }
    }
    
    try:
        # Forward to backend
        response = requests.post(
            f"{BACKEND_URL}/api/telegram/webhook",
            json=webhook_data,
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info(f"Message processed successfully: {update.message.text[:50]}")
        else:
            logger.error(f"Backend returned error: {response.status_code} - {response.text}")
            
    except Exception as e:
        logger.error(f"Error forwarding message to backend: {str(e)}")
        # Send error message to user
        await update.message.reply_text(
            "Извините, произошла ошибка. Попробуйте позже или свяжитесь с нами напрямую."
        )

def main():
    """
    Start the bot in polling mode
    """
    if not BOT_TOKEN or BOT_TOKEN == 'your_bot_token_here':
        logger.error("TELEGRAM_BOT_TOKEN not configured in .env file")
        logger.error("Please set TELEGRAM_BOT_TOKEN in /app/backend/.env")
        return
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start polling
    logger.info("Starting bot in polling mode...")
    logger.info(f"Backend URL: {BACKEND_URL}")
    logger.info("Bot is ready to receive messages!")
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
