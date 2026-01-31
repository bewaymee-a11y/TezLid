# 🚀 Запуск TezLid

## Проблема

Python и/или Node.js не настроены в PATH вашей системы Windows.

---

## Решение 1: Быстрый запуск (Рекомендуется)

### Запустите в отдельных терминалах:

**Терминал 1 - Backend:**
```powershell
cd C:\Users\beway\.gemini\antigravity\scratch\TezLid-project\backend

# Если установлен Python через py launcher:
py -m uvicorn server:app --reload --host 0.0.0.0 --port 8001

# Или если Python в PATH:
python server.py
```

**Терминал 2 - Frontend:**
```powershell
cd C:\Users\beway\.gemini\antigravity\scratch\TezLid-project\frontend
npm start
```

**Терминал 3 - Telegram Bot (опционально):**
```powershell
cd C:\Users\beway\.gemini\antigravity\scratch\TezLid-project\backend
py -m python bot_polling.py
```

---

## Решение 2: Настройка окружения

### 1. Проверьте установку Python

```powershell
py --version
# или
python --version
```

Если не работает, установите Python:
- Скачайте: https://www.python.org/downloads/
- ✅ Обязательно отметьте "Add Python to PATH"

### 2. Установите backend зависимости

```powershell
cd C:\Users\beway\.gemini\antigravity\scratch\TezLid-project\backend
py -m pip install -r requirements.txt
```

### 3. Настройте .env файл

Скопируйте `.env.example` в `.env` и заполните:
```bash
cp .env.example .env
notepad .env
```

Обязательные параметры:
- `MONGO_URL` - ваш MongoDB connection string
- `TELEGRAM_BOT_TOKEN` - токен бота
- `MANAGER_CHAT_ID` - ваш Telegram ID

### 4. Запустите приложения

Следуйте инструкциям из "Решения 1"

---

## Решение 3: Использование VS Code

1. Откройте проект в VS Code:
```powershell
cd C:\Users\beway\.gemini\antigravity\scratch\TezLid-project
code .
```

2. Откройте 3 терминала в VS Code (Terminal → Split Terminal)

3. В каждом терминале запустите:
   - Терминал 1: `cd backend && py -m uvicorn server:app --reload --port 8001`
   - Терминал 2: `cd frontend && npm start`
   - Терминал 3: `cd backend && py bot_polling.py`

---

## Что должно открыться

После успешного запуска:

- ✅ Backend API: http://localhost:8001
- ✅ Frontend Dashboard: http://localhost:3000
- ✅ CRM Integration Page: http://localhost:3000/integrations
- ✅ API Docs: http://localhost:8001/docs

---

## Проверка работы

### 1. Проверьте backend
```powershell
curl http://localhost:8001/api/stats
```

### 2. Откройте frontend
Браузер откроется автоматически на http://localhost:3000

### 3. Перейдите в CRM интеграции
http://localhost:3000/integrations

---

## Если возникли ошибки

### "Python не является внутренней командой"

**Решение:**
- Используйте `py` вместо `python`
- Или установите Python заново с опцией "Add to PATH"

### "uvicorn не найден"

**Решение:**
```powershell
py -m pip install uvicorn fastapi motor python-telegram-bot
```

### "npm не является внутренней командой"

**Решение:**
- Установите Node.js: https://nodejs.org/
- Перезапустите терминал

### "Cannot connect to MongoDB"

**Решение:**
1. Убедитесь, что MongoDB запущен
2. Проверьте `MONGO_URL` в `.env`
3. Или используйте MongoDB Atlas (облачный)

### "Module not found"

**Решение:**
```powershell
# Backend
cd backend
py -m pip install -r requirements.txt

# Frontend  
cd frontend
npm install --legacy-peer-deps
```

---

## Полная последовательность команд

```powershell
# 1. Перейдите в папку проекта
cd C:\Users\beway\.gemini\antigravity\scratch\TezLid-project

# 2. Установите backend зависимости
cd backend
py -m pip install -r requirements.txt

# 3. Настройте .env
copy .env.example .env
notepad .env  # Заполните параметры

# 4. Вернитесь в корень и установите frontend
cd ..
cd frontend
npm install --legacy-peer-deps

# 5. Запустите backend (в новом терминале)
cd ..\backend
py -m uvicorn server:app --reload --port 8001

# 6. Запустите frontend (в еще одном новом терминале)
cd ..\frontend
npm start

# 7. Откройте браузер
start http://localhost:3000
```

---

## Готово! 🎉

Теперь можете:
- Просматривать лиды на http://localhost:3000
- Настраивать CRM на http://localhost:3000/integrations
- Тестировать API на http://localhost:8001/docs

**Документация по CRM:** `CRM_INTEGRATION.md`
