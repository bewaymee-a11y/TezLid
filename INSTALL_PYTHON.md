# ⚠️ Python не установлен!

## Проблема

Python не обнаружен в вашей системе Windows.

---

## Решение: Установите Python

### Шаг 1: Скачайте Python

Перейдите на официальный сайт:
👉 **https://www.python.org/downloads/**

Скачайте последнюю версию Python 3.11 или 3.12

### Шаг 2: Установите Python

**ВАЖНО!** При установке:
✅ Обязательно отметьте галочку **"Add Python to PATH"**
✅ Выберите "Install Now"

### Шаг 3: Проверьте установку

Откройте **новый** терминал PowerShell и выполните:
```powershell
python --version
```

Должно вывести: `Python 3.x.x`

### Шаг 4: Установите зависимости

```powershell
cd C:\Users\beway\.gemini\antigravity\scratch\TezLid-project\backend
python -m pip install -r requirements.txt
```

### Шаг 5: Запустите backend

```powershell
python -m uvicorn server:app --reload --port 8001
```

---

## Временное решение: Только Frontend

Я запустил только frontend приложение. Оно откроется на:
👉 **http://localhost:3000**

Но для полноценной работы нужен backend!

### Что работает без backend:
❌ Лиды не будут загружаться
❌ CRM интеграция не работает
❌ API недоступно

### Что нужно сделать:
1. Установить Python (инструкция выше)
2. Установить зависимости backend
3. Запустить backend сервер
4. Перезагрузить frontend

---

## Быстрая установка Python (альтернатива)

### Через Microsoft Store:
1. Откройте Microsoft Store
2. Найдите "Python 3.12"
3. Нажмите "Установить"
4. После установки откройте новый терминал
5. Проверьте: `python --version`

### Через winget:
```powershell
winget install Python.Python.3.12
```

---

## После установки Python

Вернитесь к инструкции в **START_GUIDE.md** и запустите backend.

Или выполните:
```powershell
cd C:\Users\beway\.gemini\antigravity\scratch\TezLid-project\backend
python -m pip install -r requirements.txt
python -m uvicorn server:app --reload --port 8001
```

---

**Готово!** После установки Python вы сможете запустить полный стек TezLid! 🚀
