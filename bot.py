import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import database as db
import keyboards as kb
from config import BOT_TOKEN, ADMIN_IDS, RESPONSIBLE_PERSONS, SPECIAL_NOTIFICATIONS
from telegram.error import BadRequest


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)

USER_STATES = {}
application = None

# === ОСНОВНЫЕ ФУНКЦИИ ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    print(f"🆕 Пользователь {user.id} ({user.full_name}) запустил бота")
    db.add_user(telegram_id=user.id, full_name=user.full_name, username=user.username)
    USER_STATES[chat_id] = {'mode': 'user'}
    
    # Если пользователь администратор - показываем админскую клавиатуру
    if user.id in ADMIN_IDS:
        await update.message.reply_text(
            "🔧 **Панель администратора**\n\nВыберите действие:",
            reply_markup=kb.ADMIN_KEYBOARD,
            parse_mode='Markdown'
        )
        USER_STATES[chat_id] = {'mode': 'admin'}
    else:
        await update.message.reply_text(
            "🔧 **Служба оперативного ремонта ИЭФ МЛИТ**\n\nБыстро сообщайте о проблемах и отслеживайте статус заявок!\n\nВыберите действие:",
            reply_markup=kb.MAIN_KEYBOARD,
            parse_mode='Markdown'
        )

async def notify_admins_about_new_request(request_id, request_type, room, description, user_name, user_telegram_id, photo_id=None):
    """Отправляет уведомления о новой заявке с inline кнопками"""
    global application
    
    print(f"🔔 Начало отправки уведомлений для заявки #{request_id}")
    print(f"🔔 Тип заявки: {request_type}")
    print(f"🔔 SPECIAL_NOTIFICATIONS: {SPECIAL_NOTIFICATIONS}")
    
    # Определяем кому отправлять уведомления
    if request_type in SPECIAL_NOTIFICATIONS:
        notify_ids = SPECIAL_NOTIFICATIONS[request_type].copy()
        print(f"🔔 Специальное уведомление для '{request_type}': {notify_ids}")
    else:
        notify_ids = ADMIN_IDS.copy()
        print(f"🔔 Общее уведомление для '{request_type}': {notify_ids}")
    
    message = f"""
🚨 *НОВАЯ ЗАЯВКА #{request_id}*

👤 *От:* {user_name}
🚪 *Аудитория:* {room}
�� *Тип:* {request_type}
📝 *Описание:* {description}

👨‍🔧 *Ответственный:* {RESPONSIBLE_PERSONS.get(request_type, 'Дежурный')}
    """
    
    # Используем функцию из keyboards.py
    keyboard = kb.get_status_keyboard(request_id)
    
    print(f"🔔 Будет отправлено {len(notify_ids)} уведомлений")
    
    success_count = 0
    for user_id in notify_ids:
        try:
            print(f"🔔 Отправка пользователю {user_id}...")
            
            if photo_id:
                await application.bot.send_photo(
                    chat_id=user_id,
                    photo=photo_id,
                    caption=message,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                print(f"✅ Фото с кнопками отправлено пользователю {user_id}")
            else:
                await application.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                print(f"✅ Уведомление с кнопками отправлено пользователю {user_id}")
            
            success_count += 1
            
        except Exception as e:
            print(f"❌ Ошибка отправки пользователю {user_id}: {e}")
    
    print(f"🔔 Итог: отправлено {success_count}/{len(notify_ids)} уведомлений")

async def notify_user_about_status_change(request_id, new_status, admin_name):
    """Уведомляет пользователя об изменении статуса заявки"""
    try:
        global application
        print(f"🔔 Уведомление пользователя: заявка #{request_id}, статус: {new_status}")
        
        request = db.get_request_by_id(request_id)
        if not request:
            print(f"❌ Заявка #{request_id} не найдена")
            return
        
        # telegram_id теперь на позиции [10]
        user_telegram_id = request[10]
        user_name = request[11]  # full_name на позиции [11]
        
        print(f"🔔 Telegram ID пользователя: {user_telegram_id}")
        print(f"🔔 Имя пользователя: {user_name}")
        
        if not user_telegram_id:
            print(f"❌ Telegram ID не найден для заявки #{request_id}")
            return
        
        # Формируем понятное сообщение для пользователя
        if new_status == 'in_progress':
            message = f"""
🛠️ *Заявка #{request_id} взята в работу*

📋 *Номер заявки:* #{request_id}
👨‍🔧 *Исполнитель:* {admin_name}
🔄 *Статус:* В работе

Мы приступили к выполнению вашей заявки!
"""
        elif new_status == 'completed':
            message = f"""
✅ *Заявка #{request_id} выполнена*

📋 *Номер заявки:* #{request_id}  
👨‍🔧 *Исполнитель:* {admin_name}
🔄 *Статус:* Выполнена

Ваша заявка успешно выполнена!
"""
        else:
            message = f"""
🆕 *Заявка #{request_id} принята*

📋 *Номер заявки:* #{request_id}
👨‍🔧 *Исполнитель:* {admin_name}
🔄 *Статус:* Принята

Заявка принята в работу!
"""
        
        print(f"🔔 Отправка сообщения пользователю {user_telegram_id}")
        
        await application.bot.send_message(
            chat_id=user_telegram_id,
            text=message,
            parse_mode='Markdown'
        )
        
        print(f"✅ Пользователь {user_telegram_id} уведомлен о статусе: {new_status}")
        
    except Exception as e:
        print(f"❌ Ошибка уведомления пользователя: {e}")
# === АДМИНСКИЕ КОМАНДЫ ===

async def show_all_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает все заявки"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    requests = db.get_all_requests(limit=10)
    if not requests:
        await update.message.reply_text("📭 Заявок пока нет")
        return
    
    message = "📋 *Все заявки:*\n\n"
    for request in requests:
        status_emoji = {
            'new': '🆕',
            'in_progress': '🛠️', 
            'completed': '✅'
        }.get(request[6], '📋')
        
        message += f"#{request[0]} {status_emoji} {request[2]} - {request[3]}\n"
        message += f"👤 {request[11]}\n"
        message += f"📝 {request[4][:50]}...\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def show_new_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает новые заявки"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    requests = db.get_requests_by_status('new')
    if not requests:
        await update.message.reply_text("🆕 Новых заявок нет")
        return
    
    message = "🆕 *Новые заявки:*\n\n"
    for request in requests[:10]:
        message += f"#{request[0]} {request[2]} - {request[3]}\n"
        message += f"👤 {request[11]}\n"
        message += f"📝 {request[4][:50]}...\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def show_requests_in_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает заявки в работе"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    requests = db.get_requests_by_status('in_progress')
    if not requests:
        await update.message.reply_text("��️ Заявок в работе нет")
        return
    
    message = "🛠️ *Заявки в работе:*\n\n"
    for request in requests[:10]:
        message += f"#{request[0]} {request[2]} - {request[3]}\n"
        message += f"👤 {request[11]}\n"
        message += f"📝 {request[4][:50]}...\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def show_completed_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает выполненные заявки"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    requests = db.get_requests_by_status('completed')
    if not requests:
        await update.message.reply_text("✅ Выполненных заявок нет")
        return
    
    message = "✅ *Выполненные заявки:*\n\n"
    for request in requests[:10]:
        message += f"#{request[0]} {request[2]} - {request[3]}\n"
        message += f"�� {request[11]}\n"
        message += f"📝 {request[4][:50]}...\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def show_my_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает заявки текущего пользователя"""
    user = update.effective_user
    
    try:
        requests = db.get_user_requests(user.id)
        if not requests:
            await update.message.reply_text(
                "У вас пока нет заявок.", 
                reply_markup=kb.MAIN_KEYBOARD
            )
            return
        
        # Формируем сообщение БЕЗ Markdown форматирования
        message = "📊 Ваши заявки:\n\n"
        
        for request in requests[:5]:  # Показываем последние 5 заявок
            status_emoji = {
                'new': '🆕',
                'in_progress': '🛠️', 
                'completed': '✅'
            }.get(request[6], '📋')
            
            status_text = {
                'new': 'Принята',
                'in_progress': 'В работе', 
                'completed': 'Выполнена'
            }.get(request[6], 'Неизвестен')
            
            # Простой текст без форматирования
            message += f"📋 Заявка #{request[0]}\n"
            message += f"Тип: {request[2]}\n"
            message += f"Аудитория: {request[3]}\n"
            message += f"Статус: {status_emoji} {status_text}\n"
            message += f"Дата: {request[7]}\n\n"
        
        # Отправляем без parse_mode
        await update.message.reply_text(
            message, 
            reply_markup=kb.MAIN_KEYBOARD
        )
        
        print(f"✅ Показаны заявки пользователя {user.id}")
        
    except Exception as e:
        print(f"❌ Ошибка показа заявок: {e}")
        await update.message.reply_text(
            "Произошла ошибка при загрузке заявок.",
            reply_markup=kb.MAIN_KEYBOARD
        )

async def handle_status_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает изменение статуса через inline кнопки"""
    query = update.callback_query
    
    try:
        await query.answer()
        
        user = query.from_user
        if user.id not in ADMIN_IDS:
            return
        
        data = query.data
        print(f"🔔 Callback data: {data}")
        
        if not data.startswith('status_'):
            return
            
        parts = data.split('_')
        if len(parts) < 3:
            return
        
        # Извлекаем request_id и status
        request_id = parts[-1]
        status = '_'.join(parts[1:-1])
        
        # Проверяем валидность данных
        try:
            request_id = int(request_id)
        except ValueError:
            print(f"❌ Неверный request_id: {request_id}")
            return
        
        if status not in ['in_progress', 'completed']:
            print(f"❌ Неизвестный статус: {status}")
            return
        
        print(f"🔔 Изменение статуса: заявка #{request_id}, статус: {status}")
        
        # Обновляем статус в базе
        db.update_request_status(request_id, status)
        
        # Получаем информацию о заявке
        request = db.get_request_by_id(request_id)
        if not request:
            print(f"❌ Заявка #{request_id} не найдена")
            return
        
        # Формируем сообщение для админа
        status_messages = {
            'in_progress': f"🛠️ *Заявка #{request_id} взята в работу*\n\nИсполнитель: {user.full_name}",
            'completed': f"✅ *Заявка #{request_id} выполнена*\n\nИсполнитель: {user.full_name}"
        }
        
        admin_message = status_messages.get(status, f"📋 *Заявка #{request_id}*\n\nСтатус обновлен")
        
        # СОЗДАЕМ НОВУЮ КЛАВИАТУРУ В ЗАВИСИМОСТИ ОТ ТЕКУЩЕГО СТАТУСА
        if status == 'in_progress':
            # После "В работе" показываем только "Выполнено"
            new_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Выполнено", callback_data=f"status_completed_{request_id}")]
            ])
        elif status == 'completed':
            # После "Выполнено" убираем все кнопки
            new_keyboard = None
        else:
            # Для других статусов оставляем обе кнопки
            new_keyboard = kb.get_status_keyboard(request_id)
        
        # Безопасное обновление сообщения админу С КНОПКАМИ
        try:
            if new_keyboard:
                await query.edit_message_text(
                    admin_message, 
                    parse_mode='Markdown',
                    reply_markup=new_keyboard
                )
            else:
                await query.edit_message_text(
                    admin_message,
                    parse_mode='Markdown'
                )
        except Exception as e:
            # Если не можем отредактировать (сообщение с фото и т.д.)
            if new_keyboard:
                await query.message.reply_text(
                    admin_message,
                    parse_mode='Markdown',
                    reply_markup=new_keyboard
                )
            else:
                await query.message.reply_text(
                    admin_message,
                    parse_mode='Markdown'
                )
        
        # Уведомляем пользователя
        await notify_user_about_status_change(request_id, status, user.full_name)
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
async def safe_edit_message(query, text):
    """Безопасно редактирует сообщение или отправляет новое"""
    try:
        await query.edit_message_text(text)
    except Exception as e:
        print(f"DEBUG: Cannot edit message, sending new: {e}")
        try:
            await query.message.reply_text(text)
        except Exception as e2:
            print(f"DEBUG: Cannot send new message: {e2}")
# === ОБРАБОТЧИКИ СООБЩЕНИЙ ===

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    text = update.message.text
    
    print(f"📨 Сообщение от {user.id}: '{text}'")  # КАВЫЧКИ ДЛЯ ОТЛАДКИ
    
    if chat_id not in USER_STATES:
        USER_STATES[chat_id] = {'mode': 'user'}
    
    user_state = USER_STATES[chat_id]
    
    # Админские команды
    if user.id in ADMIN_IDS:
        if text == "📋 Все заявки":
            await show_all_requests(update, context)
            return
        elif text == "🆕 Новые заявки":
            await show_new_requests(update, context)
            return
        elif text == "🛠️ В работе":
            await show_requests_in_progress(update, context)
            return
        elif text == "✅ Выполненные":
            await show_completed_requests(update, context)
            return
        elif text == "📊 Статистика":
            # ДОБАВИТЬ ФУНКЦИЮ СТАТИСТИКИ
            await update.message.reply_text("📊 Статистика пока в разработке", reply_markup=kb.ADMIN_KEYBOARD)
            return
        elif text == "🔙 В главное меню":
            user_state['mode'] = 'user'
            await update.message.reply_text("Главное меню:", reply_markup=kb.MAIN_KEYBOARD)
            return
    
    # Пользовательские команды
    if text == "📝 Подать заявку":
        user_state['creating_request'] = True
        user_state['stage'] = 'type'
        print(f"🔄 Пользователь {user.id} начал создание заявки")
        await update.message.reply_text("Выберите тип проблемы:", reply_markup=kb.TYPE_KEYBOARD)
    
    elif text == "📊 Мои заявки":
        try:
            requests = db.get_user_requests(user.id)
            if not requests:
                await update.message.reply_text("У вас пока нет заявок.", reply_markup=kb.MAIN_KEYBOARD)
                return
            
            message = "📊 Ваши заявки:\n\n"
            
            for request in requests[:5]:
                status_emoji = {
                    'new': '🆕',
                    'in_progress': '🛠️', 
                    'completed': '✅'
                }.get(request[6], '📋')
                
                status_text = {
                    'new': 'Принята',
                    'in_progress': 'В работе', 
                    'completed': 'Выполнена'
                }.get(request[6], 'Неизвестен')
                
                message += f"📋 Заявка #{request[0]}\n"
                message += f"Тип: {request[2]}\n"
                message += f"Аудитория: {request[3]}\n"
                message += f"Статус: {status_emoji} {status_text}\n"
                message += f"Дата: {request[7]}\n\n"
            
            await update.message.reply_text(message, reply_markup=kb.MAIN_KEYBOARD)
            
        except Exception as e:
            print(f"❌ Ошибка показа заявок: {e}")
            await update.message.reply_text("Произошла ошибка при загрузке заявок.", reply_markup=kb.MAIN_KEYBOARD)
    
    elif text == "ℹ️ Помощь":
        await update.message.reply_text(
            "ℹ️ Помощь по боту\n\n1. Нажмите '📝 Подать заявку'\n2. Выберите тип проблемы\n3. Укажите аудиторию\n4. Опишите проблему\n\nСтатусы: 🆕 Принята, 🛠️ В работе, ✅ Выполнена",
            reply_markup=kb.MAIN_KEYBOARD
        )
    
    elif text == "📞 Контакты":
        print("🔔 Нажата кнопка Контакты")  # ОТЛАДКА
        try:
            contacts_text = "📞 Контакты ответственных лиц:\n\n"
            for problem_type, responsible in RESPONSIBLE_PERSONS.items():
                contacts_text += f"• {problem_type}: {responsible}\n"
            
            await update.message.reply_text(contacts_text, reply_markup=kb.MAIN_KEYBOARD)
            print("✅ Контакты отправлены")
            
        except Exception as e:
            print(f"❌ Ошибка в контактах: {e}")
            # ЗАПАСНОЙ ВАРИАНТ
            contacts_text = """📞 Контакты ответственных лиц:

• 🪑 Мебель: Иванов Иван - +79991234567
• 💡 Электрика: Петров Петр - +79997654321  
• 🚰 Сантехника: Сидоров Сидор - +79999876543
• 🧹 Уборка: Кузнецова Мария - +79995554433
• 🖥️ Техника: Смирнов Алексей - +79993332211
• ❓ Другое: Дежурный - +79991112233"""
            
            await update.message.reply_text(contacts_text, reply_markup=kb.MAIN_KEYBOARD)
    
    elif text == "🔙 Назад":
        if 'creating_request' in user_state:
            user_state['creating_request'] = False
        await update.message.reply_text("Главное меню:", reply_markup=kb.MAIN_KEYBOARD)
    
    elif user_state.get('creating_request'):
        await handle_request_creation(update, context, user_state, text)
    
    else:
        print(f"❌ Неизвестная команда: '{text}'")
        await update.message.reply_text("Используйте кнопки для навигации:", reply_markup=kb.MAIN_KEYBOARD)

async def handle_request_creation(update: Update, context: ContextTypes.DEFAULT_TYPE, user_state: dict, text: str):
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    print(f"🔄 Создание заявки, этап {user_state['stage']}: {text}")
    
    if user_state['stage'] == 'type':
        if text in ["🪑 Мебель", "💡 Электрика", "🚰 Сантехника", "🧹 Уборка", "🖥️ Техника", "❓ Другое"]:
            user_state['type'] = text
            user_state['stage'] = 'room'
            await update.message.reply_text("Укажите номер аудитории или кабинета:", reply_markup=kb.BACK_KEYBOARD)
    
    elif user_state['stage'] == 'room':
        user_state['room'] = text
        user_state['stage'] = 'description'
        await update.message.reply_text("Опишите проблему подробно:", reply_markup=kb.BACK_KEYBOARD)
    
    elif user_state['stage'] == 'description':
        user_state['description'] = text
        user_state['stage'] = 'photo_choice'  # НОВЫЙ ЭТАП
        await update.message.reply_text(
            "📸 Хотите прикрепить фото к заявке?\n\n"
            "Это поможет быстрее понять проблему.",
            reply_markup=kb.PHOTO_CHOICE_KEYBOARD  # Создадим эту клавиатуру
        )
    
    elif user_state['stage'] == 'photo_choice':
        if text == "📷 Прикрепить фото":
            user_state['stage'] = 'photo'
            await update.message.reply_text(
                "Отправьте фото проблемы:",
                reply_markup=kb.BACK_KEYBOARD
            )
        elif text == "📋 Без фото":
            user_state['stage'] = 'complete'
            await complete_request_creation(update, context, user_state)
        else:
            await update.message.reply_text("Пожалуйста, используйте кнопки:", reply_markup=kb.PHOTO_CHOICE_KEYBOARD)
    
    elif user_state['stage'] == 'photo':
        # Этот этап обрабатывается в handle_photo
        await update.message.reply_text("Ожидаю фото...", reply_markup=kb.BACK_KEYBOARD)

async def complete_request_creation(update: Update, context: ContextTypes.DEFAULT_TYPE, user_state: dict):
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    print(f"✅ Завершение создания заявки пользователем {user.id}")
    print(f"✅ Данные заявки: тип={user_state['type']}, аудитория={user_state['room']}, описание={user_state['description']}")
    print(f"✅ Photo ID: {user_state.get('photo_id', 'Нет фото')}")
    
    db_user = db.get_user_by_telegram_id(user.id)
    request_id = db.create_request(
        user_id=db_user[0],
        request_type=user_state['type'],
        room=user_state['room'],
        description=user_state['description'],
        photo_id=user_state.get('photo_id')
    )
    
    print(f"✅ Заявка #{request_id} создана в базе данных")
    
    # Формируем сообщение для пользователя
    message = f"""
✅ *Заявка создана!*

📋 *Номер:* #{request_id}
🚪 *Аудитория:* {user_state['room']}
🔧 *Тип:* {user_state['type']}
📝 *Описание:* {user_state['description']}
�� *Фото:* {'Прикреплено' if user_state.get('photo_id') else 'Нет'}

*Статус:* 🆕 Принята
Мы уведомим вас о ходе работ!

👨‍🔧 *Ответственный:* {RESPONSIBLE_PERSONS.get(user_state['type'], 'Дежурный')}
    """
    
    await update.message.reply_text(message, reply_markup=kb.MAIN_KEYBOARD, parse_mode='Markdown')
    
    # Отправляем уведомления администраторам
    await notify_admins_about_new_request(
        request_id=request_id,
        request_type=user_state['type'],
        room=user_state['room'],
        description=user_state['description'],
        user_name=user.full_name,
        user_telegram_id=user.id,
        photo_id=user_state.get('photo_id')
    )
    
    # Сбрасываем состояние
    USER_STATES[chat_id] = {'mode': USER_STATES[chat_id].get('mode', 'user')}

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in USER_STATES and USER_STATES[chat_id].get('creating_request'):
        user_state = USER_STATES[chat_id]
        
        if user_state.get('stage') == 'photo':
            photo = update.message.photo[-1]
            user_state['photo_id'] = photo.file_id
            user_state['stage'] = 'complete'
            
            print(f"✅ Фото добавлено к заявке пользователем {update.effective_user.id}")
            await complete_request_creation(update, context, user_state)
        else:
            await update.message.reply_text("❌ Сейчас не время для отправки фото. Завершите создание заявки.")
    else:
        await update.message.reply_text("❌ Сначала начните создание заявки через '📝 Подать заявку'")

def main():
    global application
    db.init_database()
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    
    # Обработчики inline кнопок
    application.add_handler(CallbackQueryHandler(handle_status_change, pattern='^status_'))
    
    # Обработчики сообщений (ВАЖНО: фото должно быть перед текстом!)
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("=" * 50)
    print("🤖 Бот запускается...")
    print(f"🔑 Токен: {BOT_TOKEN[:10]}...")
    print(f"👑 Главные администраторы: {ADMIN_IDS}")
    print(f"🔔 Специальные уведомления: {SPECIAL_NOTIFICATIONS}")
    print("=" * 50)
    print("⏹️  Чтобы остановить бота, нажми Ctrl+C")
    
    application.run_polling()

if __name__ == "__main__":
    main()











