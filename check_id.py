from telegram.ext import Application
from config import BOT_TOKEN

async def check_user():
    application = Application.builder().token(BOT_TOKEN).build()
    
    YOUR_CHAT_ID = 979855667
    
    try:
        # Пробуем получить информацию о чате
        chat = await application.bot.get_chat(YOUR_CHAT_ID)
        print(f"✅ Чат найден: {chat}")
        print(f"✅ Тип чата: {chat.type}")
        print(f"✅ Имя: {chat.first_name} {chat.last_name}")
        print(f"✅ Username: @{chat.username}")
        
        # Пробуем отправить сообщение
        await application.bot.send_message(
            chat_id=YOUR_CHAT_ID,
            text="🔔 Проверка связи! Если видишь это сообщение - все работает!"
        )
        print("✅ Сообщение отправлено!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        print("💡 Возможные причины:")
        print("   - Неправильный Telegram ID")
        print("   - Бот заблокирован")
        print("   - Пользователь не начинал диалог с ботом")

if __name__ == "__main__":
    import asyncio
    asyncio.run(check_user())