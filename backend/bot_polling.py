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
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters, ContextTypes
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
        # Forward to backend with retries
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/api/telegram/webhook",
                    json=webhook_data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    logger.info(f"Message processed successfully: {update.message.text[:50]}")
                    return
                else:
                    logger.error(f"Backend returned error: {response.status_code} - {response.text}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                raise
                
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                raise
                
    except Exception as e:
        logger.error(f"Error forwarding message to backend: {str(e)}")
        # Send error message to user
        await update.message.reply_text(
            "Извините, произошла ошибка при обработке вашего сообщения. "
            "Пожалуйста, попробуйте позже или свяжитесь с нами напрямую."
        )

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle inline button callbacks from manager
    
    Callback data format: lead:<lead_id>:<action>
    where action = accept | call | reject
    """
    query = update.callback_query
    
    # Answer callback query immediately to remove loading state
    await query.answer()
    
    try:
        # Parse callback data
        callback_data = query.data
        logger.info(f"Received callback: {callback_data}")
        
        # Expected format: lead:<lead_id>:<action>
        parts = callback_data.split(":")
        if len(parts) != 3 or parts[0] != "lead":
            logger.error(f"Invalid callback data format: {callback_data}")
            await query.answer("❌ Ошибка: неверный формат команды", show_alert=True)
            return
        
        _, lead_id, action = parts
        
        # Validate action
        if action not in ["accept", "call", "reject"]:
            logger.error(f"Invalid action: {action}")
            await query.answer("❌ Ошибка: неверное действие", show_alert=True)
            return
        
        # Send request to backend
        try:
            response = requests.post(
                f"{BACKEND_URL}/api/leads/{lead_id}/manager-action",
                json={"action": action},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Manager action processed: {result}")
                
                # Action names in Russian
                action_names = {
                    "accept": "✅ Заявка принята",
                    "call": "📞 Звонок запланирован",
                    "reject": "❌ Заявка отклонена"
                }
                
                action_text = action_names.get(action, "Действие выполнено")
                
                # Edit message to show action was taken (remove buttons)
                try:
                    new_text = f"{query.message.text}\n\n━━━━━━━━━━━━━━━━\n{action_text}\n⏰ {datetime.now().strftime('%H:%M:%S')}"
                    await query.edit_message_text(text=new_text)
                except Exception as e:
                    logger.warning(f"Could not edit message: {str(e)}")
                
                # Show confirmation to manager
                await query.answer(f"{action_text} ✓", show_alert=True)
                
            elif response.status_code == 404:
                logger.error(f"Lead not found: {lead_id}")
                await query.answer("❌ Лид не найден в базе", show_alert=True)
            else:
                logger.error(f"Backend error: {response.status_code} - {response.text}")
                await query.answer("❌ Ошибка сервера. Попробуйте позже.", show_alert=True)
                
        except requests.exceptions.Timeout:
            logger.error("Timeout when calling backend")
            await query.answer("❌ Превышено время ожидания. Попробуйте позже.", show_alert=True)
            
        except requests.exceptions.ConnectionError:
            logger.error("Connection error to backend")
            await query.answer("❌ Нет связи с сервером. Проверьте backend.", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error handling callback query: {str(e)}")
        await query.answer("❌ Произошла ошибка при обработке команды", show_alert=True)

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
    
    # Add callback query handler for inline buttons
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Start polling
    logger.info("Starting bot in polling mode...")
    logger.info(f"Backend URL: {BACKEND_URL}")
    logger.info("Bot is ready to receive messages and handle button clicks!")
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
