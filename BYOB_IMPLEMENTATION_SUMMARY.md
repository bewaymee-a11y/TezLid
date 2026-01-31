# BYOB Multi-Tenant Migration Summary

## ✅ Implementation Complete!

TezLid successfully migrated from single-tenant to multi-tenant BYOB (Bring Your Own Bot) model.

---

## 📝 Changes Made

### New Files Created

#### 1. [telegram_manager.py](file:///C:/Users/beway/.gemini/antigravity/scratch/TezLid-project/backend/telegram_manager.py)

**Purpose:** Manage multiple bot instances for multi-tenant support

**Key features:**
- Bot instance caching by token
- Verify bot tokens via Telegram API
- Set/delete webhooks
- Send messages with specific bot
- Send manager notifications with inline buttons
- Edit messages (remove buttons after action)
- Answer callback queries

**Usage:**
```python
from telegram_manager import telegram_manager

# Verify token
bot_info = await telegram_manager.verify_bot_token(token)

# Send message
await telegram_manager.send_message(bot_token, chat_id, text)

# Send manager notification
await telegram_manager.send_manager_notification(bot_token, manager_chat_id, lead_id, ...)
```

---

### Modified Files

#### 2. [server.py](file:///C:/Users/beway/.gemini/antigravity/scratch/TezLid-project/backend/server.py)

**Changes:**

**a) New Models:**
```python
class Company(BaseModel):
    id: str
    name: str
    bot_token: str
    bot_username: str
    manager_chat_id: int
    webhook_secret: str  # auto-generated
    webhook_url: str
    status: str  # "active" | "suspended"
    created_at: datetime
    updated_at: datetime

class ConnectTelegramRequest(BaseModel):
    bot_token: str
    manager_chat_id: int

class ConnectTelegramResponse(BaseModel):
    success: bool
    company_id: str
    bot_info: dict
    webhook_url: str
    message: str
```

**b) Updated Lead Model:**
```python
class Lead(BaseModel):
    # NEW FIELDS:
    company_id: str  # Multi-tenant isolation
    bot_id: Optional[str]  # Telegram bot ID
    
    # Existing fields...
    client_id: str
    username: str
    message: str
    lead_type: str
    status: str  # Added "accepted" status
```

**c) New Endpoints:**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/companies?name=...` | Create company & connect bot |
| POST | `/api/companies/{id}/connect-telegram` | Connect/update bot for company |
| GET | `/api/companies/{id}` | Get company info (no sensitive data) |
| DELETE | `/api/companies/{id}/disconnect-telegram` | Disconnect bot |
| POST | `/api/telegram/webhook/{company_id}/{webhook_secret}` | **Main BYOB webhook** |
| GET | `/api/leads?company_id=...` | Get leads (filtered by company) |

**d) Webhook Handler (`/telegram/webhook/{company_id}/{webhook_secret}`):**

Handles two types of updates:

**Message (lead creation):**
1. Validate company + webhook_secret
2. Extract message from Telegram update
3. Classify lead using AI
4. Save lead to DB with `company_id`
5. Send manager notification (with buttons)
6. Reply to client

**Callback Query (manager action):**
1. Validate company + webhook_secret
2. Parse callback_data: `lead:{lead_id}:{action}`
3. Validate action (accept/call/reject)
4. Update lead status in DB
5. Send client message
6. Edit manager's message (remove buttons)
7. Answer callback query

---

#### 3. [.env.example](file:///C:/Users/beway/.gemini/antigravity/scratch/TezLid-project/backend/.env.example)

**Added:**
```bash
# Base URL for webhooks (BYOB Multi-Tenant)
# For local testing with ngrok: https://xxxx.ngrok.io
# For production: https://your-domain.com
BASE_URL="http://localhost:8001"
```

---

### Documentation

#### 4. [BYOB_TESTING_GUIDE.md](file:///C:/Users/beway/.gemini/antigravity/scratch/TezLid-project/BYOB_TESTING_GUIDE.md)

Comprehensive testing guide with:
- Quick start with ngrok
- Step-by-step testing checklist
- Database verification
- API reference
- Troubleshooting

---

## 🗄️ Database Schema

### Companies Collection (NEW)

```javascript
{
  "_id": ObjectId,
  "id": "uuid",
  "name": "Company Name",
  "bot_token": "token",
  "bot_username": "@bot_name",
  "bot_first_name": "Bot Name",
  "bot_id": 1234567890,
  "manager_chat_id": 123456789,
  "webhook_secret": "random-32-chars",
  "webhook_url": "https://domain.com/telegram/webhook/{company_id}/{secret}",
  "status": "active",
  "created_at": ISODate,
  "updated_at": ISODate
}
```

### Leads Collection (UPDATED)

```javascript
{
  "_id": ObjectId,
  "id": "uuid",
  "company_id": "uuid",  // NEW: Multi-tenant isolation
  "bot_id": "1234567890",  // NEW: Bot reference
  "client_id": "123456789",
  "username": "user",
  "first_name": "Name",
  "message": "text",
  "lead_type": "hot|warm|cold",
  "service": "Service name",
  "urgency": "high|medium|low",
  "timestamp": "2026-01-31T...",
  "status": "new|accepted|contacted|rejected"  // "accepted" is NEW
}
```

---

## 🚀 How to Run Locally

### Prerequisites

1. **Backend running:**
```bash
cd C:\Users\beway\.gemini\antigravity\scratch\TezLid-project\backend
python -m uvicorn server:app --reload --port 8001
```

2. **ngrok for webhooks:**
```bash
# Download: https://ngrok.com/download
ngrok http 8001

# Copy URL (e.g., https://abc123.ngrok.io)
```

3. **Update .env:**
```bash
BASE_URL=https://abc123.ngrok.io
```

4. **Restart backend**

---

## ✅ Testing Steps

### Step 1: Create Company

```bash
curl -X POST "http://localhost:8001/api/companies?name=TestCompany" \
  -H "Content-Type: application/json" \
  -d '{
    "bot_token": "YOUR_BOT_TOKEN_FROM_BOTFATHER",
    "manager_chat_id": YOUR_TELEGRAM_CHAT_ID
  }'
```

**Expected response:**
```json
{
  "success": true,
  "company_id": "abc-123",
  "bot_info": {"username": "your_bot", ...},
  "webhook_url": "https://abc123.ngrok.io/telegram/webhook/abc-123/secret",
  "message": "Bot @your_bot connected successfully"
}
```

### Step 2: Verify Webhook

```bash
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

Should show your webhook URL.

### Step 3: Send Message to Bot

Open Telegram, send message to your bot:
```
Мне нужна консультация
```

### Step 4: Check Manager Telegram

Manager receives notification:
```
🔥 ГОРЯЧИЙ ЛИД
...
🆔 Lead ID: lead-456

[✅ Принять] [📞 Позвонить] [❌ Отказать]
```

### Step 5: Click Button

Manager clicks button → Lead status updates → Client receives message → Buttons disappear

### Step 6: Verify Database

```bash
curl "http://localhost:8001/api/leads?company_id=abc-123"
```

Should show lead with updated status.

---

## 🔑 Key Features

### ✅ Multi-Tenant Isolation

- Each company has own bot
- Leads isolated by `company_id`
- Webhook URL per company with secret
- Manager receives only their company's leads

### ✅ Secure Webhooks

- Unique `webhook_secret` per company
- Validated on every request
- 403 error if secret doesn't match

### ✅ Bot Instance Caching

`TelegramBotManager` caches Bot instances by token:
```python
{
  "token1": Bot(token1),
  "token2": Bot(token2),
  ...
}
```

Avoids recreating bots on every request.

### ✅ Manager Flow Preserved

All existing manager-flow features work:
- Inline buttons (Accept/Call/Reject)
- Lead status updates
- Client notifications
- Button removal after action

### ✅ Backward Compatible

Legacy `/api/telegram/webhook` endpoint still exists (can be deprecated).

---

## 📊 API Summary

### Company Management

**Create & Connect:**
```http
POST /api/companies?name=CompanyName
Body: {"bot_token": "...", "manager_chat_id": 123}
→ Returns: company_id, bot_info, webhook_url
```

**Get Info:**
```http
GET /api/companies/{company_id}
→ Returns: company data (no bot_token/webhook_secret)
```

**Disconnect:**
```http
DELETE /api/companies/{company_id}/disconnect-telegram
→ Deletes webhook, sets status="suspended"
```

### Leads

**Get Company Leads:**
```http
GET /api/leads?company_id={id}&status={status}
→ Returns: filtered leads
```

### Webhooks

**BYOB Webhook (auto-configured):**
```http
POST /telegram/webhook/{company_id}/{webhook_secret}
Body: Telegram Update object
→ Handles messages & callback_queries
```

---

## 🎯 Migration from Single-Tenant

If you have existing single-tenant deployment:

### Option 1: Create Default Company

```python
# Migration script
import os
import uuid
import secrets

default_company = {
    "id": str(uuid.uuid4()),
    "name": "Default Company",
    "bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
    "manager_chat_id": int(os.getenv("MANAGER_CHAT_ID")),
    "webhook_secret": secrets.token_urlsafe(32),
    "status": "active"
}

await db.companies.insert_one(default_company)

# Update existing leads
await db.leads.update_many(
    {"company_id": {"$exists": False}},
    {"$set": {"company_id": default_company["id"]}}
)

# Set webhook
base_url = os.getenv("BASE_URL")
webhook_url = f"{base_url}/telegram/webhook/{default_company['id']}/{default_company['webhook_secret']}"
await telegram_manager.set_webhook(default_company['bot_token'], webhook_url)
```

### Option 2: Start Fresh

Just create companies via API. Old data can coexist.

---

## 🔐 Security Notes

> [!WARNING]
> **Bot tokens are sensitive!**

**Current implementation:** Tokens stored in plaintext in MongoDB

**Production TODO:**
1. **Encrypt tokens** using `cryptography.fernet`
2. **Add authentication** to company management endpoints
3. **Rate limiting** on webhooks
4. **Audit logging** for all actions

**Example encryption:**
```python
from cryptography.fernet import Fernet

# Generate key once, store in env
encryption_key = os.getenv("ENCRYPTION_KEY")
cipher = Fernet(encryption_key)

# Encrypt before save
encrypted_token = cipher.encrypt(bot_token.encode())

# Decrypt when using
decrypted_token = cipher.decrypt(encrypted_token).decode()
```

---

## 📦 Files Summary

| File | Status | Purpose |
|------|--------|---------|
| `telegram_manager.py` | **NEW** | Multi-bot management |
| `server.py` | **MODIFIED** | Added Company model, endpoints, BYOB webhook |
| `.env.example` | **MODIFIED** | Added BASE_URL |
| `BYOB_TESTING_GUIDE.md` | **NEW** | Testing documentation |
| `bot_polling.py` | **DEPRECATED** | Use webhooks only |
| `telegram_bot.py` | **LEGACY** | Can be deprecated (functionality in telegram_manager) |

---

## 🎉 Success!

BYOB multi-tenant implementation is **complete** and ready for testing.

**Next steps:**
1. Install ngrok
2. Run backend
3. Set BASE_URL in .env
4. Follow `BYOB_TESTING_GUIDE.md`
5. Create your first company
6. Test full flow

**Questions?** Check the testing guide or logs!
