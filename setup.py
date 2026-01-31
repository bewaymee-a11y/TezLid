import requests
import json

def main():
    print("🚀 Настройка TezLid BYOB")
    print("-" * 30)
    
    # 1. Запрос данных
    bot_token = input("Введите токен бота (от BotFather): ").strip()
    if not bot_token:
        print("❌ Токен не может быть пустым")
        return

    chat_id_str = input("Введите ваш Chat ID (от @userinfobot): ").strip()
    if not chat_id_str:
        print("❌ Chat ID не может быть пустым")
        return
        
    try:
        chat_id = int(chat_id_str)
    except ValueError:
        print("❌ Chat ID должен быть числом")
        return

    company_name = input("Введите название компании [MyTestCompany]: ").strip() or "MyTestCompany"

    # 2. Формирование запроса
    url = "http://localhost:8002/api/companies"
    params = {"name": company_name}
    payload = {
        "bot_token": bot_token,
        "manager_chat_id": chat_id
    }

    print(f"\n📡 Подключаемся к {url}...")

    try:
        response = requests.post(url, params=params, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ УСПЕШНО!")
            print(f"Компания: {data['company_id']}")
            print(f"Бот: @{data['bot_info']['username']}")
            print(f"Webhook: {data['webhook_url']}")
            print("\n🎉 Теперь отправьте боту сообщение 'Привет'!")
        else:
            print(f"\n❌ Ошибка: {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"\n❌ Ошибка соединения: {e}")
        print("Убедитесь, что backend запущен на порту 8002")

if __name__ == "__main__":
    main()
