# BYOB Multi-Tenant Testing Guide

Comprehensive guide for testing the BYOB (Bring Your Own Bot) multi-tenant implementation.

---

## 📋 Overview

TezLid now supports multi-tenant BYOB model where each company connects their own Telegram bot to the service. Each company gets:
- Isolated lead database
- Own bot token
- Unique webhook URL with secret
- Manager chat ID configuration

---

## 🚀 Quick Start

### Prerequisites

1. **Backend running**:
   ```bash
   cd C:\Users\beway\.gemini\antigravity\scratch\TezLid-project\backend
   python -m uvicorn server:app --reload --port 8001
   ```

2. **ngrok for local testing**:
   ```bash
   # Download from https://ngrok.com/download
   ngrok http 8001
   ```
   
   You'll get a public URL like: `https://abc123.ngrok.io`

3. **Update .env**:
   ```bash
   BASE_URL=https://abc123.ngrok.io
   ```

4. **Restart backend** to apply new BASE_URL

---

## ✅ Testing Checklist

### Test 1: Create Company & Connect Bot

**1.1 Prepare Telegram Bot**

Create a bot via [@BotFather](https://t.me/BotFather):
```
/newbot
# Follow prompts
# Get bot token: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

Get your manager chat ID:
- Send message to [@userinfobot](https://t.me/userinfobot)
- Copy your chat ID (e.g., `123456789`)

**1.2 Create Company via API**

```bash
curl -X POST "http://localhost:8001/api/companies?name=TestCompany" \
  -H "Content-Type: application/json" \
  -d '{
    "bot_token": "YOUR_BOT_TOKEN",
    "manager_chat_id": YOUR_CHAT_ID
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "company_id": "abc-123-uuid",
  "bot_info": {
    "id": 1234567890,
    "username": "your_bot_name",
    "first_name": "Your Bot"
  },
  "webhook_url": "https://abc123.ngrok.io/api/telegram/webhook/abc-123-uuid/secret-here",
  "message": "Bot @your_bot_name connected successfully"
}
```

**1.3 Verify Webhook**

Check if webhook is set:
```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

**Expected:**
```json
{
  "ok": true,
  "result": {
    "url": "https://abc123.ngrok.io/api/telegram/webhook/...",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

---

### Test 2: Send Message → Create Lead

**2.1 Send message to your bot**

Open Telegram, find your bot, send:
```
Мне нужна консультация по юридическим вопросам
```

**2.2 Check backend logs**

You should see:
```
INFO - [abc-123-uuid] Received message from username: Мне нужна...
INFO - [abc-123-uuid] Lead created: lead-456-uuid
```

**2.3 Manager receives notification**

Manager (your chat) receives:
```
🔥 ГОРЯЧИЙ ЛИД

⚡ Срочность: HIGH
📋 Услуга: Юридическая консультация

👤 Клиент: YourName
✉️ Username: @yourusername
💬 ID чата: 123456789
🆔 Lead ID: lead-456-uuid

📝 Сообщен ие:
Мне нужна консультация по юридическим вопросам

⏰ Время: 2026-01-31 14:30:45

[✅ Принять] [📞 Позвонить] [❌ Отказать]
```

**2.4 Client receives auto-reply**

You (as client) receive AI-generated response:
```
Спасибо за ваш запрос! Наш менеджер свяжется с вами в ближайшее время для обсуждения юридической консультации.
```

---

### Test 3: Manager Actions

**3.1 Test "Accept" button**

Manager clicks **✅ Принять**

**Expected:**
1. Buttons disappear from manager's message
2. Message updates:
   ```
   [original message]
   
   ━━━━━━━━━━━━━━━━
   ✅ Заявка принята
   ⏰ 14:31:22
   ```
3. Manager sees popup: "✅ Заявка принята ✓"
4. Client receives: "✅ Заявка принята! Менеджер скоро свяжется с вами."

**3.2 Check database**

```bash
curl "http://localhost:8001/api/leads?company_id=abc-123-uuid"
```

Lead status should be `"accepted"`.

**3.3 Test other actions**

Send another message, test:
- 📞 Позвонить → status: `contacted`, client: "📞 Менеджер сейчас свяжется с вами по телефону."
- ❌ Отказать → status: `rejected`, client: "❌ Сейчас не можем помочь..."

---

### Test 4: Multi-Tenant Isolation

**4.1 Create second company**

```bash
curl -X POST "http://localhost:8001/api/companies?name=Company2" \
  -H "Content-Type: application/json" \
  -d '{
    "bot_token": "ANOTHER_BOT_TOKEN",
    "manager_chat_id": ANOTHER_CHAT_ID
  }'
```

**4.2 Send message to second bot**

**4.3 Verify isolation**

- Company 1's manager should NOT see Company 2's leads
- Leads are filtered by `company_id`

```bash
# Company 1 leads
curl "http://localhost:8001/api/leads?company_id=company-1-id"

# Company 2 leads  
curl "http://localhost:8001/api/leads?company_id=company-2-id"
```

---

### Test 5: Error Handling

**5.1 Invalid bot token**

```bash
curl -X POST "http://localhost:8001/api/companies?name=Test" \
  -H "Content-Type: application/json" \
  -d '{"bot_token": "invalid", "manager_chat_id": 123}'
```

**Expected:** `400 Bad Request: Invalid bot token`

**5.2 Invalid webhook secret**

```bash
curl -X POST "http://localhost:8001/telegram/webhook/abc-123/wrong-secret" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Expected:** `403 Forbidden: Invalid webhook secret`

**5.3 Unknown company**

```bash
curl -X POST "http://localhost:8001/telegram/webhook/unknown-id/secret" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Expected:** `404 Not Found: Company not found`

---

## 🗄️ Database Verification

### Check Companies Collection

```javascript
// MongoDB shell
use tezlid_db

// List all companies
db.companies.find().pretty()

// Check specific company
db.companies.findOne({id: "abc-123-uuid"})
```

**Expected structure:**
```javascript
{
  "id": "abc-123-uuid",
  "name": "TestCompany",
  "bot_token": "...",  // encrypted in production
  "bot_username": "your_bot_name",
  "bot_first_name": "Your Bot",
  "bot_id": 1234567890,
  "manager_chat_id": 123456789,
  "webhook_secret": "random-32-char-string",
  "webhook_url": "https://abc123.ngrok.io/...",
  "status": "active",
  "created_at": ISODate("2026-01-31..."),
  "updated_at": ISODate("2026-01-31...")
}
```

### Check Leads Collection

```javascript
// Leads for specific company
db.leads.find({company_id: "abc-123-uuid"}).pretty()

// Check lead structure
db.leads.findOne()
```

**Expected structure:**
```javascript
{
  "id": "lead-456-uuid",
  "company_id": "abc-123-uuid",  // NEW
  "bot_id": "1234567890",  // NEW
  "client_id": "123456789",
  "username": "yourusername",
  "first_name": "YourName",
  "message": "Мне нужна консультация...",
  "lead_type": "hot",
  "service": "Юридическая консультация",
  "urgency": "high",
  "timestamp": "2026-01-31T14:30:45Z",
  "status": "accepted"  // or "new", "contacted", "rejected"
}
```

---

## 🔧 Troubleshooting

### Webhook not receiving updates

**Check ngrok:**
```bash
# Visit http://127.0.0.1:4040 in browser
# Check "Inspect" tab for incoming requests
```

**Check webhook info:**
```bash
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

If `pending_update_count > 0`, there's an issue.

**Solution:**
1. Check backend logs for errors
2. Verify BASE_URL in .env matches ngrok URL
3. Restart backend after changing BASE_URL
4. Delete and reconnect bot

### Manager not receiving notifications

**Check:**
1. manager_chat_id is correct (not group ID)
2. Bot is started in manager's chat (send `/start` to bot first)
3. Backend logs show "Send notification to manager"

### Client not receiving messages

**Check:**
1. Bot has permission to send messages
2. Client started the bot (sent `/start`)
3. Backend logs show no Telegram API errors

---

## 📊 API Reference

### Company Management

#### Create Company
```http
POST /api/companies?name={company_name}
Content-Type: application/json

{
  "bot_token": "string",
  "manager_chat_id": number
}
```

#### Connect/Update Bot
```http
POST /api/companies/{company_id}/connect-telegram
Content-Type: application/json

{
  "bot_token": "string",
  "manager_chat_id": number
}
```

#### Get Company Info
```http
GET /api/companies/{company_id}
```

#### Disconnect Bot
```http
DELETE /api/companies/{company_id}/disconnect-telegram
```

### Leads

#### Get Company Leads
```http
GET /api/leads?company_id={company_id}&status={status}
```

### Webhooks

#### Multi-Tenant Webhook (auto-configured)
```http
POST /telegram/webhook/{company_id}/{webhook_secret}
```

This endpoint is called by Telegram, not manually.

---

## 🎉 Success Criteria

✅ Company created with bot connection  
✅ Webhook URL configured automatically  
✅ Client message creates lead  
✅ Manager receives notification with buttons  
✅ Manager action updates lead status  
✅ Client receives appropriate message  
✅ Buttons disappear after action  
✅ Multi-tenant isolation works  
✅ Leads filtered by company_id  

---

## 📝 Notes

- **ngrok session**: Free tier has 2-hour session limit. Restart if URL changes.
- **BASE_URL**: Must match exactly (https vs http, trailing slash, etc.)
- **Bot tokens**: Keep secure, don't commit to git
- **Rate limits**: Telegram has rate limits, don't spam

---

## 🔐 Production Considerations

Before deploying to production:

1. **Encrypt bot tokens** in database
2. **Use HTTPS** (required by Telegram)
3. **Add authentication** to company management endpoints
4. **Rate limiting** on webhook endpoints
5. **Monitoring** and alerts
6. **Backup strategy** for database
7. **Domain with SSL** (not ngrok)

---

## 🆘 Support

If tests fail:

1. Check backend logs: `tail -f logs/backend.log`
2. Check ngrok inspect: `http://127.0.0.1:4040`
3. Verify .env configuration
4. Test with simple curl requests first
5. Check MongoDB connection

**Common Issues:**
- `BASE_URL` not set → webhook fails
- ngrok expired → restart ngrok, reconnect bot
- Bot not started → send `/start` first
- Invalid token → check BotFather
