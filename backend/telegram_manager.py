import logging
from typing import Dict, Optional
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError
from datetime import datetime

logger = logging.getLogger(__name__)


class TelegramBotManager:
    """
    Manages multiple Telegram bot instances for multi-tenant BYOB model.
    Caches bot instances by token to avoid recreating them.
    """
    
    def __init__(self):
        self._bots: Dict[str, Bot] = {}
    
    def get_bot(self, bot_token: str) -> Bot:
        """
        Get or create Bot instance for given token.
        
        Args:
            bot_token: Telegram bot token
            
        Returns:
            Bot instance
        """
        if bot_token not in self._bots:
            self._bots[bot_token] = Bot(token=bot_token)
            logger.info(f"Created new bot instance for token ending in ...{bot_token[-10:]}")
        
        return self._bots[bot_token]
    
    async def verify_bot_token(self, bot_token: str) -> Optional[dict]:
        """
        Verify bot token by calling Telegram getMe API.
        
        Args:
            bot_token: Telegram bot token to verify
            
        Returns:
            Dict with bot info (id, username, first_name) or None if invalid
        """
        try:
            bot = Bot(token=bot_token)
            me = await bot.get_me()
            
            return {
                "id": me.id,
                "username": me.username,
                "first_name": me.first_name,
                "is_bot": me.is_bot
            }
        except TelegramError as e:
            logger.error(f"Failed to verify bot token: {str(e)}")
            return None
    
    async def set_webhook(self, bot_token: str, webhook_url: str) -> bool:
        """
        Set webhook URL for bot.
        
        Args:
            bot_token: Telegram bot token
            webhook_url: Full webhook URL
            
        Returns:
            True if successful, False otherwise
        """
        try:
            bot = self.get_bot(bot_token)
            await bot.set_webhook(url=webhook_url)
            logger.info(f"Webhook set for bot: {webhook_url}")
            return True
        except TelegramError as e:
            logger.error(f"Failed to set webhook: {str(e)}")
            return False
    
    async def delete_webhook(self, bot_token: str) -> bool:
        """
        Delete webhook for bot.
        
        Args:
            bot_token: Telegram bot token
            
        Returns:
            True if successful, False otherwise
        """
        try:
            bot = self.get_bot(bot_token)
            await bot.delete_webhook()
            logger.info(f"Webhook deleted for bot token ending in ...{bot_token[-10:]}")
            return True
        except TelegramError as e:
            logger.error(f"Failed to delete webhook: {str(e)}")
            return False
    
    async def send_message(
        self,
        bot_token: str,
        chat_id: int,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None
    ) -> bool:
        """
        Send message using specific bot.
        
        Args:
            bot_token: Telegram bot token
            chat_id: Chat ID to send to
            text: Message text
            reply_markup: Optional inline keyboard
            
        Returns:
            True if successful, False otherwise
        """
        try:
            bot = self.get_bot(bot_token)
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup
            )
            logger.info(f"Message sent to chat_id {chat_id}")
            return True
        except TelegramError as e:
            logger.error(f"Failed to send message to {chat_id}: {str(e)}")
            return False
    
    async def send_manager_notification(
        self,
        bot_token: str,
        manager_chat_id: int,
        lead_id: str,
        lead_type: str,
        service: str,
        urgency: str,
        client_name: str,
        client_username: str,
        message: str,
        chat_id: int
    ) -> bool:
        """
        Send lead notification to manager with inline action buttons.
        
        Args:
            bot_token: Telegram bot token
            manager_chat_id: Manager's chat ID
            lead_id: Lead identifier
            lead_type: Type of lead (hot/warm/cold)
            service: Service requested
            urgency: Urgency level
            client_name: Client's name
            client_username: Client's username
            message: Original message
            chat_id: Client's chat ID
            
        Returns:
            True if successful, False otherwise
        """
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
🆔 Lead ID: {lead_id}

📝 Сообщение:
{message}

⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        # Create inline keyboard with action buttons
        keyboard = [
            [
                InlineKeyboardButton("✅ Принять", callback_data=f"lead:{lead_id}:accept"),
                InlineKeyboardButton("📞 Позвонить", callback_data=f"lead:{lead_id}:call"),
                InlineKeyboardButton("❌ Отказать", callback_data=f"lead:{lead_id}:reject")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        return await self.send_message(
            bot_token=bot_token,
            chat_id=manager_chat_id,
            text=notification,
            reply_markup=reply_markup
        )
    
    async def edit_message_text(
        self,
        bot_token: str,
        chat_id: int,
        message_id: int,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None
    ) -> bool:
        """
        Edit message text (used to remove buttons after manager action).
        
        Args:
            bot_token: Telegram bot token
            chat_id: Chat ID where message is
            message_id: Message ID to edit
            text: New text
            reply_markup: Optional new keyboard (None removes buttons)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            bot = self.get_bot(bot_token)
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup
            )
            logger.info(f"Message {message_id} edited in chat {chat_id}")
            return True
        except TelegramError as e:
            logger.error(f"Failed to edit message: {str(e)}")
            return False
    
    async def answer_callback_query(
        self,
        bot_token: str,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False
    ) -> bool:
        """
        Answer callback query.
        
        Args:
            bot_token: Telegram bot token
            callback_query_id: Callback query ID
            text: Optional text to show
            show_alert: Show as alert popup
            
        Returns:
            True if successful, False otherwise
        """
        try:
            bot = self.get_bot(bot_token)
            await bot.answer_callback_query(
                callback_query_id=callback_query_id,
                text=text,
                show_alert=show_alert
            )
            return True
        except TelegramError as e:
            logger.error(f"Failed to answer callback query: {str(e)}")
            return False


# Global instance
telegram_manager = TelegramBotManager()
