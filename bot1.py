from telebot import types
from yoomoney import Quickpay, Client
import telebot
import time
import requests
import yaml
import threading
import csv
import uuid
import secrets
import telebot
import os
import subprocess
from PIL import Image, ImageOps
from io import BytesIO
import os, subprocess, time, glob
import webuiapi
import re

# Инициализируем API для инпейнтинга
# api = webuiapi.WebUIApi()
api = webuiapi.WebUIApi(host='127.0.0.1',
                        port=7860,
                        sampler='DPM++ SDE',
                        steps=40)
                        
amounts = {}
with open('amounts.txt', encoding='utf-8') as f:
  for line in f:
    line = line.strip()
    btn, name, price_name, price = line.split(';')
    amounts[btn] = {'name': name, 'price_name': price_name, 'price': int(price)}

# Чтение токена из файла
def read_token(filename):
    with open(filename, 'r') as file:
        return file.read().strip()

# Чтение текста из файла
def read_text(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        return file.read().strip()

# Получение токена из файла
token_bot = read_token('token.txt')
ADMIN_ID = 6344622092
# Получение access_token из файла
access_token = read_token('access_token.txt')
client_id = read_token('client_id.txt')

# Получение YOUR_RECEIVER из файла
your_receiver = read_token('youmoney.txt')
# Создание флага для блокировки обработки выбора тарифов
tariff_selection_in_progress = False
# Создание экземпляра бота
bot = telebot.TeleBot(token_bot)

# Удаление webhook'а
bot.delete_webhook()

# Загрузка данных о количестве обработок из файла
try:
    with open('data.yml', 'r') as file:
        users_processing = yaml.safe_load(file)
        if users_processing is None:
            users_processing = {}
except FileNotFoundError:
    users_processing = {}

# Инициализация клиента ЮMoney
token = access_token
client = Client(token)


# Функция создания ссылки на оплату
def create_payment_link(user_id, amount, label):
    receiver = your_receiver  # Номер вашего кошелька
    targets = "Sponsor this project"
    payment_type = "SB"

    quickpay = Quickpay(receiver=receiver, quickpay_form="shop", targets=targets,
                        paymentType=payment_type, sum=amount, label=label)

    return quickpay.redirected_url

# Функция проверки статуса платежа
def check_payment_status(token, label):
    client = Client(token)
    while True:
        history = client.operation_history(label=label)
        for operation in history.operations:
            if operation.status == 'success':
                return True
        time.sleep(5)  # Пауза 5 секунд перед повторной проверкой

# Функция отправки сообщения об успешной оплате
def send_payment_success_message(chat_id, count_processing):
    # Уменьшение количества обработок в зависимости от тарифа
    if count_processing == 5:
        count_processing -= 5
    elif count_processing == 1:
        count_processing -= 1
    elif count_processing == 10:
        count_processing -= 10
    elif count_processing == 50:
        count_processing -= 50

    # Сохранение данных о количестве обработок в файл
    if chat_id in users_processing:
        users_processing[chat_id]['count_processing'] += count_processing
    else:
        users_processing[chat_id] = {'user_name': bot.get_chat(chat_id).username, 'count_processing': count_processing}

    with open('data.yml', 'w') as file:
        yaml.safe_dump(users_processing, file)

    # Удаление сообщения с ссылкой на оплату
    if 'payment_message_id' in users_processing[chat_id]:
        try:
            bot.delete_message(chat_id, users_processing[chat_id]['payment_message_id'])
        except Exception as e:
            print(f"Ошибка удаления сообщения: {str(e)}")

    # Отправка сообщения об успешной оплате
    message_text = f"✅ Платеж успешный. Количество обработок: {users_processing[chat_id]['count_processing']}"
    bot.send_message(chat_id, message_text)

    # Отправка дополнительного сообщения администратору
    admin_chat_id = ADMIN_ID  # Замените на переменную, содержащую идентификатор администратора
    admin_message_text = f"Пользователь {chat_id} (@{users_processing[chat_id]['user_name']}) совершил успешный платеж.\nКоличество обработок: {users_processing[chat_id]['count_processing']}"
    bot.send_message(admin_chat_id, admin_message_text)


# Функция сохранения данных в файл data.yml
def save_user_data(data):
    with open('data.yml', 'w') as file:
        yaml.safe_dump(data, file)

@bot.message_handler(commands=['give'])
def give_processing(message):
    # Проверяем, является ли отправитель администратором
    if message.from_user.id == ADMIN_ID:
        # Разделяем команду на аргументы (user_id и количество обработок)
        command_args = message.text.split()
        if len(command_args) == 3:
            user_id = int(command_args[1])
            processing_count = int(command_args[2])

            if user_id in users_processing:
                users_processing[user_id]['count_processing'] += processing_count  # Увеличение количества обработок пользователя
            else:
                users_processing[user_id] = {'user_name': bot.get_chat(user_id).username, 'count_processing': processing_count}

            update_data_yml()  # Обновление данных в файле data.yml

            # Отправка сообщения администратору о успешной выдаче обработок
            admin_message = f"✅ Пользователю с ID {user_id} было выдано {processing_count} обработок. Текущее количество обработок: {users_processing[user_id]['count_processing']}"
            bot.reply_to(message, admin_message)

            # Отправка сообщения пользователю о получении обработок
            user_message = f"✅ Вы получили {processing_count} обработок. Текущее количество обработок: {users_processing[user_id]['count_processing']}"
            bot.send_message(user_id, user_message)
        else:
            bot.reply_to(message, "Неверный формат команды. Используйте /give <user_id> <количество>")
    else:
        bot.reply_to(message, "У вас нет доступа к этой команде.")

@bot.message_handler(commands=['give1'])
def give_processing(message):
    # Проверяем, является ли отправитель администратором
    if message.from_user.id == ADMIN_ID:
        # Разделяем команду на аргументы (user_id и количество обработок)
        command_args = message.text.split()
        if len(command_args) == 3:
            user_id = int(command_args[1])
            processing_count = int(command_args[2])

            if user_id in users_processing:
                users_processing[user_id]['count_processing'] += processing_count  # Увеличение количества обработок пользователя
            else:
                users_processing[user_id] = {'user_name': bot.get_chat(user_id).username, 'count_processing': processing_count}

            update_data_yml()  # Обновление данных в файле data.yml

            # Отправка сообщения администратору о успешной выдаче обработок
            admin_message = f"✅ Пользователю с ID {user_id} было выдано {processing_count} обработок. Текущее количество обработок: {users_processing[user_id]['count_processing']}"
            bot.reply_to(message, admin_message)

        else:
            bot.reply_to(message, "Неверный формат команды. Используйте /give1 <user_id> <количество>")
    else:
        bot.reply_to(message, "У вас нет доступа к этой команде.")


@bot.message_handler(content_types=['photo'], func=lambda message: message.from_user.id == ADMIN_ID)
def handle_admin_photo(message):
    send_message_with_attachment(message)

@bot.message_handler(content_types=['photo'], func=lambda message: message.from_user.id != ADMIN_ID)
def handle_user_photo(message):
    user_id = message.from_user.id
    user_name = message.from_user.username

    if user_id in users_processing:
        count_processing = users_processing[user_id]['count_processing']
        if count_processing > 0:
            # Отправка фото администратору с уникальным кодом пользователя
            admin_id = ADMIN_ID
            message_id = message.message_id 
            text = message.caption
            # Скачиваем фото
            file_id = message.photo[-1].file_id
            file_path = bot.get_file(file_id).file_path
            downloaded_file = bot.download_file(file_path)
            # Сохраняем фото
            src = '/content/images/' + file_id + '.jpg'
            with open(src, 'wb') as new_file:
                new_file.write(downloaded_file)
            unique_code = f"{secrets.token_hex(5)}"
            caption = f"ID: <code>{user_id}</code>\nНик: @{user_name}\nЗаказ: <code>{unique_code}</code>"
            photo_id = message.photo[-1].file_id
            keyboard = types.InlineKeyboardMarkup()
            refuse_button = types.InlineKeyboardButton('Отказать', callback_data='refuse_photo')
            keyboard.add(refuse_button)
            bot.send_photo(admin_id, message.photo[-1].file_id, caption=caption, parse_mode='HTML', reply_markup=keyboard)
            admin_message_id = message.message_id
            message_text = f"✅ Фотография принята, ожидайте...\n\n📦 Заказ номер: <code>{unique_code}</code>\n🌐 Тех.Поддержка - @razdde"
            bot.send_message(chat_id=user_id, text=message_text, parse_mode='HTML', reply_to_message_id=message_id)
            users_processing[user_id]['count_processing'] -= 1  # Уменьшение количества обработок пользователя
            update_data_yml()  # Обновление данных в файле data.yml
            try:
                # Выполняем скрипт для создания маски
                lib_command  = [
                    "python3",
                    "/content/detecthuman/simple_extractor.py",  # Проверьте путь к скрипту
                    "--dataset", "lip",
                    "--model-restore", "lib/lib.pth",
                    "--input-dir", "images",
                    "--output-dir", "lib_results"
                ]
                subprocess.run(lib_command)   
                lib_mask_path = 'lib_results/' + file_id + '.png'
                lib_mask = Image.open(lib_mask_path).convert("L")
                # Применяем инпейнтинг
                result2_path = 'images/' + file_id + '.jpg'  # Путь к вашему result2 изображению
                mask = Image.open(lib_mask_path)
                result2 = Image.open(result2_path)
                inpainting_result = api.img2img(images=[result2],
                                                mask_image=mask,
                                                inpainting_fill=10,
                                                cfg_scale=2.0,
                                                prompt="naked woman without clothes, naked breasts, naked vagina, excessive detail, (skin pores: 1.1), (skin with high detail: 1.2), (skin shots: 0.9), film grain, soft lighting, high quality",
                                                negative_prompt="(deformed, distorted, disfigured:1.3), poorly drawn, bad anatomy, wrong anatomy, extra limb, missing limb, floating limbs, (mutated hands and fingers:1.4), disconnected limbs, mutation, mutated, ugly, disgusting, blurry, amputation",
                                                denoising_strength=0.9)
                # Отправляем результат пользователю
                with BytesIO() as buf:
                    inpainting_result.image.save(buf, format='PNG')
                    buf.seek(0)
                    bot.send_photo(message.chat.id, photo=buf, caption="✅ Фотография успешно обработана! Тех.Поддержка - @razdde")
                  
                # Отправляем результат администратору  
                
                with BytesIO() as buf:
                    inpainting_result.image.save(buf, format='PNG')
                    buf.seek(0)
                    caption = f"ID: <code>{user_id}</code>\nНик: @{user_name}\nЗаказ: <code>{unique_code}</code>"
                    bot.send_photo(admin_id, photo=buf, caption=caption, parse_mode='HTML')
              
                # Удаляем файлы
                os.remove(src)
                os.remove(lib_mask_path)
            except subprocess.CalledProcessError as e:
                print("Ошибка при выполнении команды:", e)
                
        else:
            keyboard = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton('🛒 Купить обработку', callback_data='buy_processing1')
            keyboard.add(button)
            bot.send_message(message.chat.id, "⛔ У вас недостаточно обработок. Чтобы купить обработки, нажмите на кнопку ниже 👇", reply_markup=keyboard, parse_mode='HTML')
    else:
        bot.send_message(message.chat.id, "Профиль пользователя не найден.")


@bot.callback_query_handler(func=lambda call: call.data == 'buy_processing1')
def buy_processing_callback(call):
    user_id = call.from_user.id
    # Логика обработки нажатия на кнопку "Купить обработку"
    if user_id not in users_processing:
        users_processing[user_id] = {'user_name': bot.get_chat(user_id).username, 'count_processing': 0}

    # Удаление сообщения "⛔ У вас недостаточно обработок. Чтобы купить обработки, нажмите на кнопку ниже 👇"
    bot.delete_message(call.message.chat.id, call.message.message_id)

    # Создание клавиатуры с кнопками тарифов
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    button1 = types.InlineKeyboardButton(amounts['button1']['name'], callback_data='tariff_1')
    button2 = types.InlineKeyboardButton(f"{amounts['button1']['price_name']}", callback_data='tariff_1')
    button3 = types.InlineKeyboardButton(amounts['button2']['name'], callback_data='tariff_2')
    button4 = types.InlineKeyboardButton(f"{amounts['button2']['price_name']}", callback_data='tariff_2')
    button5 = types.InlineKeyboardButton(amounts['button3']['name'], callback_data='tariff_3')
    button6 = types.InlineKeyboardButton(f"{amounts['button3']['price_name']}", callback_data='tariff_3')
    button7 = types.InlineKeyboardButton(amounts['button4']['name'], callback_data='tariff_4')
    button8 = types.InlineKeyboardButton(f"{amounts['button4']['price_name']}", callback_data='tariff_4')
    keyboard.add(button1, button2)
    keyboard.add(button3, button4)
    keyboard.add(button5, button6)
    keyboard.add(button7, button8)

    # Формирование сообщения с количеством обработок и выбором тарифа
    count_processing = users_processing[user_id]['count_processing']
    message_text = f"Количество обработок: {count_processing}\n\n<b>Выберите тариф:</b>"
    bot.send_message(call.message.chat.id, text=message_text, reply_markup=keyboard, parse_mode='HTML')

# Функция обновления данных в файле data.yml
def update_data_yml():
    with open('data.yml', 'w') as file:
        yaml.safe_dump(users_processing, file)


# Функция отправки сообщения с прикрепленными файлами
def send_message_with_attachment(message):
    # Проверяем, является ли отправитель администратором
    if message.from_user.id == ADMIN_ID:
        photo = message.photo[0].file_id
        caption = message.caption

        if caption:
            items = caption.split()
            if items[0] == '/photo':
                text = ' '.join(items[2:])
                bot.send_photo(int(items[1]), photo, caption=text)
            elif items[0] == '/true':
                true_text = "✅ Ваша фотография успешно обработана! Тех.Поддержка - @razdde"
                bot.send_photo(int(items[1]), photo, caption=true_text)
            elif items[0] == '/false':
                false_text = "❌ Ваша фотография не подходит! Выберите другое фото. Тех.Поддержка - @razdde"
                bot.send_photo(int(items[1]), photo, caption=false_text)
                deduct_processing(int(items[1]))  # Вычет обработки из базы данных
            else:
                bot.reply_to(message, "Неверный формат команды.")
        else:
            bot.reply_to(message, "Подпись к фото отсутствует.")

@bot.message_handler(commands=['allsend'])
def handle_allsend(message):
    global waiting_for_broadcast
    if message.from_user.id == admin_id:
        bot.send_message(message.chat.id, "Введите текст сообщения для массовой рассылки:")
        waiting_for_broadcast = True
    else:
        bot.send_message(message.chat.id, "У вас нет прав для выполнения этой команды.")


@bot.callback_query_handler(func=lambda call: call.data == 'refuse_photo')
def refuse_photo(call):

    user_id = call.message.caption.split('\n')[0].split(': ')[-1].strip()

    items = call.message.caption.split()

    photo_id = call.message.photo[-1].file_id

    bot.send_photo(user_id, photo_id, caption="❌ Ваша фотография не подходит! Выберите другое фото. Тех.Поддержка - @razdde")

    deduct_processing(int(items[1]))

    refusal_caption = "❌ Фото отклонено"
    bot.edit_message_caption(chat_id=call.message.chat.id,
                             message_id=call.message.message_id,
                             caption=call.message.caption + "\n" + refusal_caption)

# Функция вычета обработки из базы данных
def deduct_processing(user_id):

    if user_id in users_processing:

       users_processing[user_id]['count_processing'] += 1

       with open('data.yml', 'w') as file:
           yaml.safe_dump(users_processing, file)

       message_text = "✅ Одна обработка вернулась на счет."
       bot.send_message(user_id, message_text)

    else:
       bot.send_message(user_id, "Профиль пользователя не найден.")

@bot.message_handler(commands=['start'])
def start(message):
    # Регистрация пользователя в базе данных
    user_id = message.from_user.id
    if user_id not in users_processing:
        users_processing[user_id] = {'user_name': bot.get_chat(user_id).username, 'count_processing': 1}

        # Добавление нового пользователя в файл
        with open('data.yml', 'a') as file:
            file.write(f'\n- user_id: {user_id}\n user_name: {users_processing[user_id]["user_name"]}\n count_processing: {users_processing[user_id]["count_processing"]}')

    # Создание клавиатуры с кнопками
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton('🔞 Раздеть девушку')
    button2 = types.KeyboardButton('🛒 Купить обработки')
    button3 = types.KeyboardButton('💼 Профиль')
    button4 = types.KeyboardButton('📃 Инструкция')
    support_button = types.KeyboardButton('♻️ Тех.Поддержка')
    keyboard.add(button1, button3)
    keyboard.add(button2, button4)
    keyboard.add(support_button)

    with open('start.txt', encoding='utf-8') as f:
        caption = f.read()
        
    # Создание инлайн-кнопки и добавление ее к приветственному сообщению
    inline_button = types.InlineKeyboardButton('👀 Посмотреть примеры', callback_data='show_examples')
    inline_keyboard = types.InlineKeyboardMarkup()
    inline_keyboard.add(inline_button)
    start_photo = open('start.jpg', 'rb')
    text = "👋"
    # Отправка приветственного сообщения с клавиатурой и инлайн-кнопкой
    bot.send_message(message.chat.id, text, reply_markup=keyboard)
    bot.send_photo(message.chat.id, photo=start_photo, caption=caption, reply_markup=inline_keyboard)

    # Сохранение данных в файл
    save_data()

@bot.message_handler(func=lambda message: message.text == '♻️ Тех.Поддержка')
def support(message):
    support_text = 'По вопросам обращайтесь в поддержку:'
    inline_button = types.InlineKeyboardButton('♻️ Тех.Поддержка', url='https://t.me/razdde')
    inline_keyboard = types.InlineKeyboardMarkup()
    inline_keyboard.add(inline_button)
    bot.send_message(message.chat.id, support_text, reply_markup=inline_keyboard)



# Обработчик кнопки "Показать примеры"
@bot.callback_query_handler(func=lambda call: call.data == 'show_examples')
def show_examples(call):
    user_id = call.from_user.id
    photo_files = ['photo1.jpg', 'photo2.jpg', 'photo3.jpg', 'photo4.jpg', 'photo5.jpg', 'photo6.jpg']
    for photo_file in photo_files:
        with open(photo_file, 'rb') as photo:
            bot.send_photo(call.message.chat.id, photo)
    bot.send_message(call.message.chat.id, "👇 Выбери действие:")


@bot.message_handler(func=lambda message: message.text == '📃 Инструкция')
def send_instructions(message):
    user_id = message.from_user.id
    if user_id in users_processing:
        user_name = users_processing[user_id]['user_name']
        count_processing = users_processing[user_id]['count_processing']

    with open('info.txt', 'r', encoding='utf-8') as file:
        instructions = file.read()

    # Создание инлайн-кнопки и добавление ее к сообщению с инструкциями
    inline_button = types.InlineKeyboardButton('♻️ Тех.Поддержка', url='https://t.me/razdde')
    inline_keyboard = types.InlineKeyboardMarkup()
    inline_keyboard.add(inline_button)

    bot.send_message(message.chat.id, instructions)
    bot.send_message(message.chat.id, 'Если у вас возникли вопросы или проблемы, обратитесь в техническую поддержку:', reply_markup=inline_keyboard)


# Обработчик нажатия на кнопку "Купить обработку"
@bot.message_handler(func=lambda message: message.text == '🛒 Купить обработки')
def buy_processing(message):
    # Регистрация пользователя в базе данных
    user_id = message.from_user.id
    if user_id not in users_processing:
        users_processing[user_id] = {'user_name': bot.get_chat(user_id).username, 'count_processing': 0}

        # Добавление нового пользователя в файл
        with open('data.yml', 'a') as file:
            file.write(f'\n- user_id: {user_id}\n user_name: {users_processing[user_id]["user_name"]}\n count_processing: {users_processing[user_id]["count_processing"]}')



        # Добавление нового пользователя в файл
        with open('data.yml', 'a') as file:
            file.write(f'{user_id}\n user_name: {users_processing[user_id]["user_name"]}\n count_processing: {users_processing[user_id]["count_processing"]}')

    # Создание клавиатуры с кнопками тарифов
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    button1 = types.InlineKeyboardButton(amounts['button1']['name'], callback_data='tariff_1')
    button2 = types.InlineKeyboardButton(f"{amounts['button1']['price_name']}", callback_data='tariff_1')
    button3 = types.InlineKeyboardButton(amounts['button2']['name'], callback_data='tariff_2')
    button4 = types.InlineKeyboardButton(f"{amounts['button2']['price_name']}", callback_data='tariff_2')
    button5 = types.InlineKeyboardButton(amounts['button3']['name'], callback_data='tariff_3')
    button6 = types.InlineKeyboardButton(f"{amounts['button3']['price_name']}", callback_data='tariff_3')
    button7 = types.InlineKeyboardButton(amounts['button4']['name'], callback_data='tariff_4')
    button8 = types.InlineKeyboardButton(f"{amounts['button4']['price_name']}", callback_data='tariff_4')
    keyboard.add(button1, button2)
    keyboard.add(button3, button4)
    keyboard.add(button5, button6)
    keyboard.add(button7, button8)

    # Формирование сообщения с количеством обработок и выбором тарифа
    count_processing = users_processing[user_id]['count_processing']
    message_text = f"Количество обработок: {count_processing}\n\n<b>Выберите тариф:</b>"
    bot.send_message(message.chat.id, text=message_text, reply_markup=keyboard, parse_mode='HTML')

    # Сохранение данных в файл
    save_data()

# Обработчик команды /send
@bot.message_handler(commands=['send'])
def send_message_with_image(message):
    # Проверяем, является ли отправитель администратором
        # Разделяем команду на аргументы (айди пользователя и текст сообщения)
        command_args = message.text.split()
        if len(command_args) >= 3:
            user_id = int(command_args[1])
            text = ' '.join(command_args[2:])

            # Отправка сообщения пользователю
            bot.send_message(user_id, text)

            # Проверка на наличие изображения в сообщении
            if message.photo:
                # Получение идентификатора изображения
                photo_id = message.photo[-1].file_id
                # Отправка изображения пользователю
                bot.send_photo(user_id, photo_id)

            # Проверка на наличие прикрепленного файла
            if message.document:
                # Получение идентификатора файла
                file_id = message.document.file_id
                # Отправка файла пользователю
                bot.send_document(user_id, file_id)
        else:
            bot.reply_to(message, "Неверный формат команды. Используйте /send <user_id> <текст>")


# Обработчик нажатия на кнопку "💼 Профиль"
@bot.message_handler(func=lambda message: message.text == '💼 Профиль')
def show_profile(message):
    user_id = message.from_user.id
    if user_id in users_processing:
        user_name = users_processing[user_id]['user_name']
        count_processing = users_processing[user_id]['count_processing']

        # Формирование текста профиля
        profile_text = f"🏠 ID: <code>{user_id}</code>\n👑 Количество обработок: <b>{count_processing}</b>\n\n🌐 Тех.Поддержка - @razdde"
        profile_text += f"\n👉 Наш канал - @razdevanie_devyshec"

        # Отправка сообщения с профилем пользователя
        bot.send_message(message.chat.id, profile_text, parse_mode='HTML', disable_web_page_preview=True)
    else:
        # Если пользователя нет в базе данных, добавляем его с информацией по умолчанию
        user_name = message.from_user.username
        users_processing[user_id] = {'user_name': user_name, 'count_processing': 0}

        # Записываем обновленные данные в файл data.yml
        save_user_data(users_processing)
        show_profile(message)
# Обработчик нажатия на кнопку "🔞 Раздеть девушку"
@bot.message_handler(func=lambda message: message.text == '🔞 Раздеть девушку')
def request_photo(message):
    user_id = message.from_user.id
    if user_id in users_processing:
        user_name = users_processing[user_id]['user_name']
        count_processing = users_processing[user_id]['count_processing']
        if count_processing > 0:
            bot.send_message(message.chat.id, "<b>Отправьте фото:</b>", parse_mode='HTML')
        else:
            keyboard = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton('🛒 Купить обработку', callback_data='buy_processing')
            keyboard.add(button)
            insufficient_message = bot.send_message(message.chat.id, "⛔ У вас недостаточно обработок. Чтобы купить обработки, нажмите на кнопку ниже 👇", reply_markup=keyboard, parse_mode='HTML')

    else:
        # Если пользователя нет в базе данных, добавляем его с информацией по умолчанию
        user_name = message.from_user.username
        users_processing[user_id] = {'user_name': user_name, 'count_processing': 0}

        # Записываем обновленные данные в файл data.yml
        save_user_data(users_processing)

        request_photo(message)

# Обработчик нажатия на кнопку "Купить обработку"
@bot.callback_query_handler(func=lambda call: call.data == 'buy_processing')
def handle_buy_processing(call):
    user_id = call.from_user.id
    # Логика обработки нажатия на кнопку "Купить обработку"
    if user_id not in users_processing:
        users_processing[user_id] = {'user_name': bot.get_chat(user_id).username, 'count_processing': 0}

    # Удаление сообщения "⛔ У вас недостаточно обработок. Чтобы купить обработки, нажмите на кнопку ниже 👇"
    bot.delete_message(call.message.chat.id, call.message.message_id)

    # Создание клавиатуры с кнопками тарифов
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    button1 = types.InlineKeyboardButton(amounts['button1']['name'], callback_data='tariff_1')
    button2 = types.InlineKeyboardButton(f"{amounts['button1']['price_name']}", callback_data='tariff_1')
    button3 = types.InlineKeyboardButton(amounts['button2']['name'], callback_data='tariff_2')
    button4 = types.InlineKeyboardButton(f"{amounts['button2']['price_name']}", callback_data='tariff_2')
    button5 = types.InlineKeyboardButton(amounts['button3']['name'], callback_data='tariff_3')
    button6 = types.InlineKeyboardButton(f"{amounts['button3']['price_name']}", callback_data='tariff_3')
    button7 = types.InlineKeyboardButton(amounts['button4']['name'], callback_data='tariff_4')
    button8 = types.InlineKeyboardButton(f"{amounts['button4']['price_name']}", callback_data='tariff_4')
    keyboard.add(button1, button2)
    keyboard.add(button3, button4)
    keyboard.add(button5, button6)
    keyboard.add(button7, button8)

    # Формирование сообщения с количеством обработок и выбором тарифа
    count_processing = users_processing[user_id]['count_processing']
    message_text = f"Количество обработок: {count_processing}\n\n<b>Выберите тариф:</b>"
    bot.send_message(call.message.chat.id, text=message_text, reply_markup=keyboard, parse_mode='HTML')

def load_data():
    global users_processing
    with open('data.yml', 'r') as file:
        users_processing = yaml.safe_load(file) or {}

# Функция для сохранения данных в файл
def save_data():
    with open('data.yml', 'w') as file:
        yaml.safe_dump(users_processing, file)

@bot.message_handler(commands=['stat'])
def show_stat(message):
    # Проверяем, является ли отправитель администратором
    if message.from_user.id == ADMIN_ID:
        num_users = len(users_processing)
        bot.reply_to(message, f"👤 Зарегистрированных пользователей: {num_users}")
    else:
        bot.reply_to(message, "У вас нет доступа к этой команде.")

# Обработчик команды /send
@bot.message_handler(commands=['send'])
def send_message_with_attachment1(message):
    # Проверяем, является ли отправитель администратором
        # Разделяем команду на аргументы (айди пользователя и текст сообщения)
        command_args = message.text.split()
        if len(command_args) >= 3:
            user_id = int(command_args[1])
            text = ' '.join(command_args[2:])

            # Отправка сообщения пользователю
            bot.send_message(user_id, text)

            # Проверка на наличие прикрепленных файлов
            if message.photo:
                # Отправка всех прикрепленных фотографий
                for photo in message.photo:
                    photo_id = photo.file_id
                    bot.send_photo(user_id, photo_id)

            if message.document:
                # Отправка всех прикрепленных документов
                for document in message.document:
                    document_id = document.file_id
                    bot.send_document(user_id, document_id)
        else:
            bot.reply_to(message, "Неверный формат команды. Используйте /send <user_id> <текст>")

# Обработчик команды /info
@bot.message_handler(commands=['info'])
def show_user_info(message):
    # Проверяем, является ли отправитель администратором
    if message.from_user.id == ADMIN_ID:
        # Разделяем команду на аргументы (user_id)
        command_args = message.text.split()
        if len(command_args) == 2:
            user_id = int(command_args[1])
            if user_id in users_processing:
                count_processing = users_processing[user_id]['count_processing']
                user_name = users_processing[user_id]['user_name']  # Получение ника пользователя
                user_info_text = f"ID пользователя: <code>{user_id}</code>\nНик пользователя: @{user_name}\nКоличество обработок: <b>{count_processing}</b>"
                bot.send_message(message.chat.id, user_info_text, parse_mode='HTML')
            else:
                bot.send_message(message.chat.id, "Профиль пользователя не найден.")
        else:
            bot.send_message(message.chat.id, "Неверный формат команды. Используйте /info <user_id>")
    else:
        bot.send_message(message.chat.id, "У вас нет доступа к этой команде.")


# Функция проверки статуса платежа в отдельном потоке
def check_payment_status_thread(token, label, user_id, count_processing):
    if check_payment_status(token, label):
        # Начисление обработок и отправка сообщения об успешной оплате
        users_processing[user_id]['count_processing'] += count_processing
        send_payment_success_message(user_id, count_processing)
        print("Платеж успешный")
    else:
        bot.send_message(user_id, "Платеж неуспешный. Пожалуйста, попробуйте еще раз.")
        print("Платеж неуспешный")

# Обработчик команды /all
@bot.message_handler(commands=['all'])
def send_message_to_all(message):
    # Проверяем, является ли отправитель администратором
    if message.from_user.id == ADMIN_ID:
        # Получение текста сообщения и прикрепленного файла (если есть)
        command_args = message.text.split(maxsplit=1)
        if len(command_args) == 2:
            text = command_args[1]
            document = message.document
            photo = message.photo

            # Отправка сообщения всем пользователям
            for user_id in users_processing:
                try:
                    if text:
                        bot.send_message(user_id, text)
                    if document:
                        bot.send_document(user_id, document.file_id)
                    if photo:
                        bot.send_photo(user_id, photo[-1].file_id)
                except Exception as e:
                    print(f"Ошибка при отправке сообщения пользователю {user_id}: {str(e)}")

        else:
            bot.reply_to(message, "Неверный формат команды. Используйте /all <сообщение>")
    else:
        bot.reply_to(message, "У вас нет доступа к этой команде.")

@bot.callback_query_handler(func=lambda call: True)
def handle_tariff_selection(call):
    # Получение данных из колбэка
    callback_data = call.data.split('_')
    user_id = call.from_user.id  # ID пользователя

    if callback_data[0] == 'tariff':
        tariff = callback_data[1]  # Номер тарифа
        amount = 0  # Сумма платежа
        count_processing = 0  # Количество обработок

        # Определение суммы платежа и количества обработок в зависимости от тарифа
        if tariff == '1':
            amount = amounts['button1']['price']  # Сумма для первого тарифа
            count_processing = 1
        elif tariff == '2':
            amount = amounts['button2']['price']  # Сумма для второго тарифа
            count_processing = 5
        elif tariff == '3':
            amount = amounts['button3']['price']  # Сумма для третьего тарифа
            count_processing = 10
        elif tariff == '4':
            amount = amounts['button4']['price']  # Сумма для четвертого тарифа
            count_processing = 50

        if amount > 0:
            # Создание ссылки на оплату в сервисе ЮMoney
            label = f"user_{user_id}_{int(time.time())}"  # Уникальный комментарий плательщика
            payment_url = create_payment_link(user_id, amount, label)  # Создание ссылки на оплату

            if payment_url:
                message_text = f"<b>Количество обработок:</b> {count_processing}\n\n<b>К оплате:</b> {amount} RUB"
                keyboard = types.InlineKeyboardMarkup(row_width=2)
                card_payment_button = types.InlineKeyboardButton('💳 Банковской картой', url=payment_url)
                other_payment_button = types.InlineKeyboardButton('♻️ Другое', callback_data='other_payment')
                keyboard.add(card_payment_button)
                keyboard.add(other_payment_button)
                payment_message = bot.send_message(user_id, message_text, reply_markup=keyboard, parse_mode='HTML')
                bot.delete_message(call.message.chat.id, call.message.message_id)

                # Проверка успешности платежа в отдельном потоке
                payment_status_thread = threading.Thread(target=check_payment_status_thread, args=(token, label, user_id, count_processing))
                payment_status_thread.start()
            else:
                bot.send_message(user_id, "Ошибка при создании платежа. Пожалуйста, попробуйте еще раз.")
        else:
            bot.send_message(user_id, "Выбран неправильный тариф. Пожалуйста, повторите выбор.")
    elif call.data == 'other_payment':
        # Создание инлайн-кнопки и добавление ее к сообщению с инструкциями
        inline = types.InlineKeyboardMarkup()
        inline_button = types.InlineKeyboardButton('♻ Тех.Поддержка', url='https://t.me/razdde')
        inline.add(inline_button)
        bot.send_message(user_id, "🔗 Для оплаты другими сервисами свяжитесь с Тех.Поддержкой - @razdde", reply_markup=inline)
        bot.delete_message(call.message.chat.id, call.message.message_id)



# Запуск бота
bot.polling(1000000)