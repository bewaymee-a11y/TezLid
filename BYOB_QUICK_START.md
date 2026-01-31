# BYOB Quick Start Guide

3-минутная инструкция для запуска BYOB multi-tenant TezLid.

---

## 🚀 Запуск

### 1. Установите ngrok

```bash
# Windows: скачайте с https://ngrok.com/download
# Распакуйте и добавьте в PATH
```

### 2. Запустите ngrok

```bash
ngrok http 8001
```

Скопируйте URL типа: `https://abc123.ngrok.io`

### 3. Обновите .env

```bash
cd C:\Users\beway\.gemini\antigravity\scratch\TezLid-project\backend
notepad .env
```

Добавьте/обновите:
```
BASE_URL=https://abc123.ngrok.io
```

### 4. Запустите backend

```bash
python -m uvicorn server:app --reload --port 8001
```

---

## 📱 Создайте бота

### 1. Telegram → @BotFather

```
/newbot
# Имя: My Test Bot
# Username: mytestbot_123
# Получите токен: 1234567890:ABCdef...
```

### 2. Узнайте свой chat_id

Telegram → @userinfobot → Send any message → Copy chat ID (например: `123456789`)

---

## 🔗 Подключите бота

```bash
curl -X POST "http://localhost:8001/api/companies?name=TestCompany" \
  -H "Content-Type: application/json" \
  -d "{\"bot_token\": \"YOUR_BOT_TOKEN\", \"manager_chat_id\": YOUR_CHAT_ID}"
```

**Замените:**
- `YOUR_BOT_TOKEN` → ваш токен от BotFather
- `YOUR_CHAT_ID` → ваш chat ID

**Ответ:**
```json
{
  "success": true,
  "company_id": "abc-123",
  "webhook_url": "https://abc123.ngrok.io/telegram/webhook/abc-123/secret",
  "message": "Bot @mytestbot_123 connected successfully"
}
```

---

## ✅ Тестируйте!

### 1. Откройте Telegram → найдите вашего бота

### 2. Отправьте сообщение:
```
Мне нужна консультация
```

### 3. Проверьте:

✅ **Вы получаете** (как клиент):
```
Спасибо за ваш запрос! Наш менеджер свяжется с вами...
```

✅ **Вы получаете** (как менеджер):
```
🔥 ГОРЯЧИЙ ЛИД
...
🆔 Lead ID: ...

[✅ Принять] [📞 Позвонить] [❌ Отказать]
```

### 4. Нажмите кнопку

Например: **✅ Принять**

✅ **Кнопки исчезают**  
✅ **Вы получаете**: "✅ Заявка принята! Менеджер скоро свяжется с вами."

---

## 🎉 Готово!

Вы настроили multi-tenant BYOB!

**Что дальше:**
- Добавьте больше компаний (повторите шаг "Подключите бота ")
- Проверьте базу: `db.companies.find()` и `db.leads.find()`
- Читайте полную документацию: `BYOB_TESTING_GUIDE.md`

---

## ⚠️ Troubleshooting

**Webhook не работает?**
- Проверьте ngrok работает: `http://127.0.0.1:4040` → Inspect
- Убедитесь BASE_URL = ngrok URL
- Перезапустите backend после изменения .env

**Manager не получает уведомления?**
- Отправьте `/start` вашему боту
- Проверьте chat_id правильный
- Проверьте логи backend

**Client не получает ответы?**
- Отправьте `/start` вашему боту
- Проверьте логи backend на ошибки

---

## 📚 Документация

- **Полное руководство:** [BYOB_TESTING_GUIDE.md](file:///C:/Users/beway/.gemini/antigravity/scratch/TezLid-project/BYOB_TESTING_GUIDE.md)
- **Технический обзор:** [BYOB_IMPLEMENTATION_SUMMARY.md](file:///C:/Users/beway/.gemini/antigravity/scratch/TezLid-project/BYOB_IMPLEMENTATION_SUMMARY.md)
- **Walkthrough:** [byob_walkthrough.md](file:///C:/Users/beway/.gemini/antigravity/brain/1bf76624-49f1-499b-af53-8612ff516b80/byob_walkthrough.md)
