# Manager-Flow Testing Checklist

Quick reference for testing the manager-flow implementation.

## Prerequisites
- [ ] Backend running on http://localhost:8001
- [ ] Bot polling running (`python bot_polling.py`)
- [ ] MongoDB accessible
- [ ] Valid bot token and manager chat ID in `.env`

## Basic Functionality Tests

### ✅ Accept Button
- [ ] Create lead by sending message to bot
- [ ] Manager receives notification with buttons
- [ ] Lead ID is visible in notification
- [ ] Click "✅ Принять" button
- [ ] Buttons disappear from message
- [ ] Manager sees "✅ Заявка принята" with timestamp
- [ ] Client receives acceptance message
- [ ] Database shows status = "accepted"

### 📞 Call Button  
- [ ] Create new lead
- [ ] Click "📞 Позвонить" button
- [ ] Buttons removed
- [ ] Manager sees "📞 Звонок запланирован"
- [ ] Client receives call notification
- [ ] Database shows status = "contacted"

### ❌ Reject Button
- [ ] Create new lead
- [ ] Click "❌ Отказать" button
- [ ] Buttons removed
- [ ] Manager sees "❌ Заявка отклонена"
- [ ] Client receives rejection message
- [ ] Database shows status = "rejected"

## Error Handling Tests

### Backend Offline
- [ ] Stop backend server
- [ ] Create lead and click button
- [ ] Manager sees connection error message

### Invalid Data
- [ ] Check logs for proper error handling
- [ ] Verify no crashes on invalid callback data

## Security Verification
- [ ] `.env` not in git repository
- [ ] `.env` in `.gitignore`
- [ ] `.env.example` has no sensitive data

## Performance Checks
- [ ] Button clicks respond within 2 seconds
- [ ] No duplicate messages to client
- [ ] Logs show successful flow completion

---

**All tests passing?** ✅ Manager-flow is ready for production!
