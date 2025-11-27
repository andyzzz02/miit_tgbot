from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

# Основные клавиатуры
MAIN_KEYBOARD = ReplyKeyboardMarkup([
    ["📝 Подать заявку", "📊 Мои заявки"],
    ["ℹ️ Помощь", "📞 Контакты"]
], resize_keyboard=True)

TYPE_KEYBOARD = ReplyKeyboardMarkup([
    ["🪑 Мебель", "💡 Электрика", "🚰 Сантехника"],
    ["🧹 Уборка", "🖥️ Техника", "❓ Другое"],
    ["🔙 Назад"]
], resize_keyboard=True)

BACK_KEYBOARD = ReplyKeyboardMarkup([["🔙 Назад"]], resize_keyboard=True)

# Клавиатуры для администраторов
ADMIN_KEYBOARD = ReplyKeyboardMarkup([
    ["📋 Все заявки", "🆕 Новые заявки", "🛠️ В работе"],
    ["✅ Выполненные", "📊 Статистика"],
    ["🔙 В главное меню"]
], resize_keyboard=True)

STATUS_KEYBOARD = ReplyKeyboardMarkup([
    ["🛠️ Взять в работу", "✅ Выполнено"],
    ["🔙 К заявкам"]
], resize_keyboard=True)
# Клавиатура для выбора фото
PHOTO_CHOICE_KEYBOARD = ReplyKeyboardMarkup([
    ["📷 Прикрепить фото", "📋 Без фото"],
    ["🔙 Назад"]
], resize_keyboard=True)

# Inline клавиатуры для быстрого изменения статуса
def get_status_keyboard(request_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛠️ В работу", callback_data=f"status_in_progress_{request_id}"),
            InlineKeyboardButton("✅ Выполнено", callback_data=f"status_completed_{request_id}")
        ]
    ])
