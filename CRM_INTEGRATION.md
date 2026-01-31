# 🔗 CRM Integration Guide

## Обзор

TezLid теперь поддерживает интеграцию с внешними CRM системами через:

- **Webhooks** - автоматическая отправка лидов в вашу CRM
- **API** - программный доступ к данным через REST API
- **Bidirectional Sync** - двусторонняя синхронизация

---

## Поддерживаемые CRM системы

### 1. **AmoCRM** 🇷🇺
Популярная российская CRM система

**Настройка:**
1. Получите Client ID и Client Secret в настройках AmoCRM
2. Используйте OAuth для получения Access Token
3. Укажите домен (например, `mycompany.amocrm.ru`)

### 2. **Bitrix24** 🇷🇺  
Платформа для управления бизнесом

**Настройка:**
1. Создайте входящий вебхук в Bitrix24
2. Скопируйte URL вебхука
3. Вставьте URL в настройках интеграции

### 3. **Custom Webhook** 🌐
Любая CRM с поддержкой вебхуков

**Настройка:**
1. Укажите URL эндпоинта вашей CRM
2. Выберите метод (POST/PUT)
3. Добавьте заголовки (если нужны)

---

## Быстрый старт

### Шаг 1: Откройте интерфейс управления

Перейдите в раздел **CRM Интеграции** в веб-интерфейсе:
```
http://localhost:3000/integrations
```

### Шаг 2: Создайте интеграцию

1. Нажмите **"New Integration"**
2. Выберите тип CRM
3. Заполните необходимые поля
4. Нажмите **"Create"**

### Шаг 3: Протестируйте

1. Нажмите кнопку **"Test"** рядом с интеграцией
2. TezLid отправит тестовый лид в вашу CRM
3. Проверьте, что лид появился в вашей системе

---

## API Endpoints

### Управление интеграциями

```http
# Создать интеграцию
POST /api/crm/integrations
Content-Type: application/json

{
  "name": "My CRM",
  "integration_type": "webhook",
  "config": {
    "endpoint": "https://your-crm.com/webhook",
    "method": "POST",
    "headers": {
      "X-API-Key": "your-key"
    }
  },
  "events": ["lead.created", "lead.updated"]
}

# Получить список интеграций
GET /api/crm/integrations?enabled_only=true

# Обновить интеграцию
PUT /api/crm/integrations/{integration_id}

# Удалить интеграцию
DELETE /api/crm/integrations/{integration_id}

# Тестировать интеграцию
POST /api/crm/integrations/{integration_id}/test
```

### API Keys

```http
# Создать API ключ
POST /api/api-keys
Content-Type: application/json

{
  "name": "My App",
  "permissions": ["read", "write"],
  "rate_limit": 1000,
  "expires_days": 365
}

Response:
{
  "key": "tlk_xxxxxxxxxxxxx",  // Сохраните! Больше не покажется
  "name": "My App",
  "permissions": ["read", "write"],
  "rate_limit": 1000,
  "expires_at": "2027-01-30T..."
}

# Список ключей
GET /api/api-keys

# Отозвать ключ
DELETE /api/api-keys/{key_hash}
```

### External API (требует API Key)

```http
# Заголовок авторизации
Authorization: Bearer tlk_xxxxxxxxxxxxx

# Получить лиды
GET /api/external/leads?status=new&limit=50

# Получить конкретный лид
GET /api/external/leads/{lead_id}

# Создать лид
POST /api/external/leads
Content-Type: application/json

{
  "client_id": "123456789",
  "username": "user",
  "first_name": "John",
  "message": "Interested in service",
  "lead_type": "warm",
  "service": "Consulting",
  "urgency": "medium",
  "status": "new"
}

# Обновить лид
PUT /api/external/leads/{lead_id}
Content-Type: application/json

{
  "status": "contacted"
}
```

---

## Формат Webhook Payload

Когда создается или обновляется лид, TezLid отправляет webhook:

```json
{
  "event": "lead.created",
  "timestamp": "2026-01-30T20:50:49+05:00",
  "lead": {
    "id": "uuid",
    "client_id": "123456789",
    "username": "client_username",
    "first_name": "Client Name",
    "message": "Original message text",
    "lead_type": "hot|warm|cold",
    "service": "Service name",
    "urgency": "high|medium|low",
    "status": "new|contacted|converted|rejected",
    "timestamp": "2026-01-30T15:30:00Z"
  }
}
```

---

## Примеры интеграций

### Пример 1: Custom Webhook

```javascript
// Node.js сервер для приёма вебхуков
const express = require('express');
const app = express();

app.post('/webhook/tezlid', express.json(), (req, res) => {
  const { event, lead } = req.body;
  
  console.log(`Received event: ${event}`);
  console.log(`Lead type: ${lead.lead_type}`);
  console.log(`Service: ${lead.service}`);
  
  // Обработайте лид в вашей CRM
  // ...
  
  res.json({ status: 'received' });
});

app.listen(3000);
```

### Пример 2: Bitrix24

**URL вебхука:**
```
https://your-company.bitrix24.ru/rest/1/xxxxxx/crm.lead.add.json
```

**Автоматически создаётся лид с полями:**
- Заголовок: Название услуги
- Имя: Имя клиента
- Комментарий: Текст сообщения
- Пользовательские поля: Telegram ID, тип лида, срочность

### Пример 3: AmoCRM

Требуется настройка OAuth. После получения токенов:

```json
{
  "name": "AmoCRM Integration",
  "integration_type": "amocrm",
  "config": {
    "domain": "mycompany.amocrm.ru",
    "client_id": "xxx",
    "client_secret": "xxx",
    "access_token": "xxx",
    "refresh_token": "xxx"
  }
}
```

---

## Логи и мониторинг

### Просмотр логов вебхуков

В интерфейсе перейдите на вкладку **"Webhook Logs"**:

- ✅ Успешные отправки
- ❌ Ошибки
- ⏱️ Время отправки
- 📝 Детали запроса/ответа

### Программный доступ к логам

```http
GET /api/crm/webhooks/logs?integration_id=crm_123&limit=100
```

---

## Безопасность

### API Keys
- Генерируются случайным образом (32 байта)
- Хранятся в виде SHA-256 хэша
- Отображаются один раз при создании
- Поддерживают ограничение запросов

### Webhook Signature (опционально)

Добавьте в `.env`:
```bash
CRM_WEBHOOK_SECRET=your_random_secret_key
```

TezLid будет подписывать вебхуки HMAC-SHA256.

---

## Решение проблем

### Вебхук не доходит до CRM

1. Проверьте URL эндпоинта
2. Проверьте логи вебхуков
3. Убедитесь, что эндпоинт доступен из интернета
4. Проверьте заголовки авторизации

### API ключ не работает

1. Проверьте формат заголовка: `Authorization: Bearer tlk_xxx`
2. Убедитесь, что ключ не истёк
3. Проверьте права доступа ключа

### Лиды не отправляются автоматически

1. Убедитесь, что интеграция включена (`enabled: true`)
2. Проверьте, что событие `lead.created` в списке событий
3. Проверьте логи backend на наличие ошибок

---

## Настройки `.env`

Добавьте в `backend/.env`:

```bash
# CRM Integration
CRM_WEBHOOK_SECRET=change_this_to_random_secret
CRM_RETRY_ATTEMPTS=3
CRM_TIMEOUT=30

# AmoCRM (опционально)
AMOCRM_DOMAIN=mycompany.amocrm.ru
AMOCRM_CLIENT_ID=
AMOCRM_CLIENT_SECRET=

# Bitrix24 (опционально)
BITRIX24_WEBHOOK_URL=
```

---

## Что дальше?

- [ ] Добавить больше CRM провайдеров (Salesforce, HubSpot)
- [ ] Расширенный mapping полей через UI
- [ ] Автоматическая синхронизация статусов
- [ ] Webhook retry dashboard
- [ ] Rate limiting visualization

---

## Поддержка

Если возникли вопросы:
1. Проверьте логи: `tail -f /var/log/supervisor/backend.*.log`
2. Проверьте webhook logs в интерфейсе
3. Проверьте API key permissions

**Готово!** 🎉 Ваша CRM теперь подключена к TezLid!
