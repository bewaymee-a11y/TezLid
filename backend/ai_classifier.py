import os
from dotenv import load_dotenv
import google.generativeai as genai
import json
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Initialize AI
api_key = os.environ.get('EMERGENT_LLM_KEY') or os.environ.get('GOOGLE_API_KEY')
if api_key:
    genai.configure(api_key=api_key)

SYSTEM_PROMPT = """Ты — AI-ассистент для классификации лидов малого бизнеса.

Твоя задача:
1. Определить, является ли сообщение потенциальным лидом (lead: true/false)
2. Классифицировать тип лида:
   - "hot" (горячий): клиент готов купить сейчас, хочет цену/оформить заказ
   - "warm" (тёплый): интересуется, уточняет детали, но ещё не готов купить
   - "cold" (холодный): общий вопрос, просто узнаёт информацию
3. Определить услугу/продукт, который интересует клиента
4. Определить срочность:
   - "high": нужно срочно, сегодня/завтра
   - "medium": в ближайшие дни
   - "low": без спешки, планирует заранее
5. Сгенерировать вежливый и профессиональный ответ клиенту

Ответы должны быть:
- Короткими (1-3 предложения)
- Вежливыми и профессиональными
- Подтверждающими, что менеджер свяжется
- Без эмодзи

Формат ответа СТРОГО JSON:
{
  "lead": true/false,
  "lead_type": "hot"/"warm"/"cold",
  "service": "название услуги",
  "urgency": "high"/"medium"/"low",
  "reply": "текст ответа клиенту"
}

Если сообщение — не лид (приветствие, благодарность, спам), верни lead: false и короткий вежливый ответ."""

async def classify_lead(message: str, session_id: str) -> dict:
    """
    Classifies a message as a lead using AI
    
    Args:
        message: The message text from the client
        session_id: Unique session ID (chat_id)
    
    Returns:
        dict with classification results
    """
    try:
        # Initialize Gemini model
        model = genai.GenerativeModel('gemini-pro')
        
        # Create prompt
        prompt = f"""{SYSTEM_PROMPT}

Сообщение от клиента: {message}

Ответь ТОЛЬКО JSON, без дополнительного текста."""
        
        # Get AI response
        response = model.generate_content(prompt)
        response_text = response.text
        logger.info(f"AI Response: {response_text}")
        
        
        # Parse JSON response
        try:
            # Clean response - remove markdown code blocks if present
            clean_response = response_text.strip()
            if clean_response.startswith('```'):
                # Remove ```json and ``` markers
                clean_response = clean_response.split('\n', 1)[1] if '\n' in clean_response else clean_response
                clean_response = clean_response.rsplit('```', 1)[0].strip()
            
            classification = json.loads(clean_response)
            
            # Validate required fields
            if 'lead' not in classification:
                classification['lead'] = False
            if 'reply' not in classification:
                classification['reply'] = 'Спасибо за ваше сообщение! Наш менеджер свяжется с вами в ближайшее время.'
            
            # Set defaults for non-leads
            if not classification['lead']:
                classification['lead_type'] = 'cold'
                classification['service'] = 'Не применимо'
                classification['urgency'] = 'low'
            
            return classification
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {response}. Error: {e}")
            # Return default response
            return {
                "lead": True,
                "lead_type": "warm",
                "service": "Требуется уточнение",
                "urgency": "medium",
                "reply": "Спасибо за ваше сообщение! Наш менеджер свяжется с вами в ближайшее время для уточнения деталей."
            }
    
    except Exception as e:
        logger.error(f"Error in AI classification: {str(e)}")
        # Return safe default
        return {
            "lead": True,
            "lead_type": "warm",
            "service": "Не определено",
            "urgency": "medium",
            "reply": "Спасибо за ваше сообщение! Мы получили ваш запрос и свяжемся с вами в ближайшее время."
        }