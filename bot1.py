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
from PIL import ImageFilter
import queue
from queue import Queue
import asyncio
# Инициализируем API
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

def read_token(filename):
    with open(filename, 'r') as file:
        return file.read().strip()
        
token_bot = read_token('token.txt')
ADMIN_ID = 6697285192
access_token = '4100110982154501.870D6D03180DF717261ABD00E6C3F4DE4965FAF8158A32959F3EC1E29716A5F024F2CF0C746EFF4C0EFABC00D4663F8BD51A52C59EBCAA2CFCFD716856EB228CDAD786AEC88FDAB2C459993303F4A8309490CAC1B224B3B8CA4D113F4D4773F05D2415E3DD5DC220495AF0DD4BC0B3D3FB93512DAE2BC64B9B3B9DBD12F92768'
your_receiver = '4100110982154501'
tariff_selection_in_progress = False
bot = telebot.TeleBot(token_bot)
bot.delete_webhook()
# Инициализация клиента ЮMoney
token = access_token
client = Client(token)

# Загрузка данных о количестве обработок из файла
try:
    with open('data.yml', 'r') as file:
        users_processing = yaml.safe_load(file)
        if users_processing is None:
            users_processing = {}
except FileNotFoundError:
    users_processing = {}



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
    message_text = f"✅ Платеж успешный.\n💰 Пополнение на: <code>{count_processing}</code> обработок\n\n🏠 У вас: <code>{users_processing[chat_id]['count_processing']}</code> обработок"
    bot.send_message(chat_id, text=message_text, parse_mode='HTML')
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


    # Отправка дополнительного сообщения администратору
    admin_chat_id = ADMIN_ID  # Замените на переменную, содержащую идентификатор администратора
    admin_message_text = f"Пользователь {chat_id} (@{users_processing[chat_id]['user_name']}) совершил успешный платеж.\nКоличество обработок: {users_processing[chat_id]['count_processing']}"
    bot.send_message(admin_chat_id, admin_message_text)

    update_data_yml()


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
                users_processing[user_id] = {
                    'user_name': bot.get_chat(user_id).username,
                    'count_processing': 0,
                    'free': 0,
                    'ref': 0,
                    'ref1': 0
                }
            update_data_yml()  # Обновление данных в файле data.yml

            try:
                # Отправка сообщения пользователю о получении обработок
                user_message = f"✅ Получено <b>{processing_count}</b> обработок.\n🏠 У вас: <b>{users_processing[user_id]['count_processing']}</b> обработок"
                bot.send_message(chat_id=user_id, text=user_message, parse_mode='HTML')
                admin_message = f"✅ ID {user_id} выдано {processing_count} обработок. Текущее количество обработок: {users_processing[user_id]['count_processing']}"
                bot.reply_to(message, admin_message)
            except Exception as e:
                admin_message = f"(не зареган) ✅  ID {user_id} выдано {processing_count} обработок. Текущее количество обработок: {users_processing[user_id]['count_processing']}"
                bot.reply_to(message, admin_message)
        else:
            bot.reply_to(message, "Неверный формат команды. Используйте /give <user_id> <количество>")
    else:
        bot.reply_to(message, "У вас нет доступа к этой команде.")


@bot.message_handler(content_types=['photo'], func=lambda message: message.from_user.id == ADMIN_ID)
def handle_admin_photo(message):
    send_message_with_attachment(message)

task_queue = queue.Queue()

# Функция для обработки фотографии
def process_photo(admin_id, unique_code, message, photo_result, user_id, file_id, message_id, user_name, wait_mes_id, caption, count_processing, free_processing, users_processing, ADMIN_ID):
    try:
        keyboard_admin = types.InlineKeyboardMarkup()
        refuse_button = types.InlineKeyboardButton('Отмена', callback_data='cancel_photo_1')
        keyboard_admin.add(refuse_button)

        keyboard_user = types.InlineKeyboardMarkup()
        buy_button = types.InlineKeyboardButton('🛒 Купить обработки', callback_data='buy_processing2')
        keyboard_user.add(buy_button)
      
        message_text2 = f"⌛ <b>Сканирование, ожидайте...</b>"
        bot.edit_message_text(chat_id=user_id, message_id=wait_mes_id, text=message_text2, parse_mode='HTML')

        lib_command = [
            "python3",
            "/content/detecthuman/simple_extractor.py",
            "--dataset", "lip",
            "--model-restore", "lib/lib.pth",
            "--input-dir", "images",
            "--output-dir", "lib_results"
        ]
        subprocess.run(lib_command)
        
        lib_results_folder = 'lib_results/'
        file_list = os.listdir(lib_results_folder)
        lib_mask_path = 'lib_results/' + file_id + '.png'
        lib_mask = Image.open(lib_mask_path).convert("L")
        
        # Применяем инпейнтинг
        result2_path = 'images/' + file_id + '.jpg'
        mask = Image.open(lib_mask_path)
        result2 = Image.open(result2_path)

        message_text4 = f"⌛ <b>Генерация, ожидайте...</b>"
        bot.edit_message_text(chat_id=user_id, message_id=wait_mes_id, text=message_text4, parse_mode='HTML')

        inpainting_result = api.img2img(images=[result2],
                                        mask_image=mask,
                                        inpainting_fill=10,
                                        cfg_scale=2.0,
                                        prompt="naked woman without clothes, naked breasts, naked vagina, excessive detail, (skin pores: 1.1), (skin with high detail: 1.2), (skin shots: 0.9), film grain, soft lighting, high quality",
                                        negative_prompt="(deformed, distorted, disfigured:1.3), poorly drawn, bad anatomy, wrong anatomy, extra limb, missing limb, floating limbs, (mutated hands and fingers:1.4), disconnected limbs, mutation, mutated, ugly, disgusting, blurry, amputation",
                                        denoising_strength=0.9)

        # Отправляем результат пользователю
        with BytesIO() as buf:
            if photo_result == "not_censorship":
                final_result = inpainting_result.image
                caption = f"✅ Фотография обработана."
                final_result.save(buf, format='PNG')
                buf.seek(0)
                bot.delete_message(chat_id=user_id, message_id=wait_mes_id)
                bot.send_photo(message.chat.id, photo=buf, caption=caption, parse_mode='HTML')

            else:
                blurred_result = inpainting_result.image.filter(ImageFilter.GaussianBlur(radius=10))
                final_result = blurred_result
                caption = f"✅ Фотография успешно обработана!\n\n💳 Купите обработки, чтобы получить результат без цензуры 👇"
                final_result.save(buf, format='PNG')
                buf.seek(0)
                bot.delete_message(chat_id=user_id, message_id=wait_mes_id)
                bot.send_photo(message.chat.id, photo=buf, caption=caption, parse_mode='HTML', reply_markup=keyboard_user)

        # Отправляем результат администратору
        with BytesIO() as buf_admin:
            final_result.save(buf_admin, format='PNG')
            buf_admin.seek(0)
            caption_admin = f"ID: <code>{user_id}</code>\nНик: @{user_name}\nЗаказ: <code>{unique_code}</code>\nОбработок: <code>{users_processing[user_id]['count_processing']}</code>\n♻️Результат♻️"
            bot.send_photo(admin_id, photo=buf_admin, caption=caption_admin, parse_mode='HTML', reply_markup=keyboard_admin)

        # Удаляем файлы
        os.remove(src)
        # Пройтись по списку и удалить каждый файл
        for file_name in file_list:
            file_path = os.path.join(lib_results_folder, file_name)
            if os.path.isfile(file_path):
                os.remove(file_path)
                
    except Exception as e:
        print("An error occurred:", str(e))
        if photo_result == "not_censorship":
            bot.delete_message(chat_id=user_id, message_id=wait_mes_id)
            users_processing[user_id]['count_processing'] += 1
            bot.send_message(chat_id=user_id, text='❌ Ошибка. Отправьте другое фото.', reply_to_message_id=message_id) 
        if photo_result == "censorship":
            bot.delete_message(chat_id=user_id, message_id=wait_mes_id)
            users_processing[user_id]['free'] += 1
            bot.send_message(chat_id=user_id, text='❌ Ошибка. Отправьте другое фото.', reply_to_message_id=message_id)
                  
        with open('data.yml', 'w') as file:
            yaml.safe_dump(users_processing, file)
                    



# Функция для обработки очереди задач
def process_queue():
    while True:
        admin_id, unique_code, message, photo_result, user_id, file_id, message_id, user_name, wait_mes_id, caption, count_processing, free_processing, users_processing, ADMIN_ID = task_queue.get()
        process_photo(admin_id, unique_code, message, photo_result, user_id, file_id, message_id, user_name, wait_mes_id, caption, count_processing, free_processing, users_processing, ADMIN_ID)
        task_queue.task_done()

# Запускаем обработку очереди в отдельном потоке
queue_thread = threading.Thread(target=process_queue)
queue_thread.start()

 
# Функция для обработки сообщения пользователя с фотографией
@bot.message_handler(content_types=['photo'], func=lambda message: message.from_user.id != ADMIN_ID)
def handle_user_photo(message):
    user_id = message.from_user.id
    user_name = message.from_user.username

    if user_id in users_processing:
        count_processing = users_processing[user_id]['count_processing']
        free_processing = users_processing[user_id]['free']

        if count_processing > 0 or free_processing == 1:
            admin_id = ADMIN_ID
            message_id = message.message_id 
            text = message.caption
            file_id = message.photo[-1].file_id
            file_path = bot.get_file(file_id).file_path
            downloaded_file = bot.download_file(file_path)

            # Сохраняем фото
            src = 'images/' + file_id + '.jpg'
            with open(src, 'wb') as new_file:
                new_file.write(downloaded_file)

            unique_code = f"{secrets.token_hex(5)}"
            caption = f"ID: <code>{user_id}</code>\nНик: @{user_name}\nОбработок: <code>{users_processing[user_id]['count_processing']}</code>"

            keyboard_user = types.InlineKeyboardMarkup()
            buy_button = types.InlineKeyboardButton('🛒 Купить обработки', callback_data='buy_processing2')
            keyboard_user.add(buy_button)
            keyboard_admin = types.InlineKeyboardMarkup()
            refuse_button = types.InlineKeyboardButton('Отмена', callback_data='cancel_photo')
            keyboard_admin.add(refuse_button)
            if count_processing > 0:
                # Замыляем результат
                photo_result = "not_censorship"
                # Обновляем информацию о пользователе перед отправкой результата
                users_processing[user_id]['free'] = 0
                users_processing[user_id]['count_processing'] -= 1   
                update_data_yml()
            else:
                # Оставляем результат без замыления                  
                photo_result = "censorship"
                # Обновляем информацию о пользователе перед отправкой результата
                users_processing[user_id]['free'] = 0
                update_data_yml()             

            # Отправляем фото администратору с соответствующей клавиатурой
            bot.send_photo(admin_id, message.photo[-1].file_id, caption=caption, parse_mode='HTML', reply_markup=keyboard_admin)
            admin_message_id = message.message_id
            message_text1 = f"⌛ <b>Вы в очереди, ожидайте...</b>\n\n~Примерное время одижадние: <b>15 секунд</b>"
            wait_mes = bot.send_message(chat_id=user_id, text=message_text1, parse_mode='HTML', reply_to_message_id=message_id)
            wait_mes_id = wait_mes.message_id

            # Добавляем задачу в очередь для обработки
            task_queue.put((admin_id, unique_code, message, photo_result, user_id, file_id, message_id, user_name, wait_mes_id, caption, count_processing, free_processing, users_processing, ADMIN_ID))

        else:
            keyboard = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton('🛒 Купить обработки', callback_data='buy_processing1')
            keyboard.add(button)
            bot.send_message(message.chat.id, "⛔ У вас недостаточно обработок. Чтобы купить обработки, нажмите на кнопку ниже 👇", reply_markup=keyboard, parse_mode='HTML')

    else:
        bot.send_message(message.chat.id, "Требуется перезагрузка - /start")
        

@bot.callback_query_handler(func=lambda call: call.data == 'cancel_photo_1')
def cancel_photo_1(call):

  user_id = call.message.caption.split('\n')[0].split(': ')[-1].strip()
  items = call.message.caption.split()
  photo_id = call.message.photo[-1].file_id
  bot.send_photo(user_id, photo_id, caption="❌ Обработка отмененна. Отправь фото еще раз.")
  deduct_processing(int(items[1]))
  refusal_caption = "❌ Фото отклонено"
  bot.edit_message_caption(chat_id=call.message.chat.id,
                           message_id=call.message.message_id,
                           caption=call.message.caption + "\n" + refusal_caption)
  
@bot.callback_query_handler(func=lambda call: call.data == 'cancel_photo')
def cancel_photo(call):

  user_id = call.message.caption.split('\n')[0].split(': ')[-1].strip()
  items = call.message.caption.split()
  photo_id = call.message.photo[-1].file_id
  bot.send_photo(user_id, photo_id, caption="❌ Некорректная обработка. Фотография отклонена.")
  deduct_processing(int(items[1]))
  refusal_caption = "❌ Фото отклонено"
  bot.edit_message_caption(chat_id=call.message.chat.id,
                           message_id=call.message.message_id,
                           caption=call.message.caption + "\n" + refusal_caption)


@bot.callback_query_handler(func=lambda call: call.data == 'buy_processing2')
def buy_processing_callback(call):
    user_id = call.from_user.id
    # Логика обработки нажатия на кнопку "Купить обработку"
    if user_id not in users_processing:
        users_processing[user_id] = {
            'user_name': bot.get_chat(user_id).username,
            'count_processing': 0,
            'free': 0,
            'ref': 0,
            'ref1': 0
        }


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

@bot.callback_query_handler(func=lambda call: call.data == 'buy_processing1')
def buy_processing_callback(call):
    user_id = call.from_user.id
    # Логика обработки нажатия на кнопку "Купить обработку"
    if user_id not in users_processing:
        users_processing[user_id] = {
            'user_name': bot.get_chat(user_id).username,
            'count_processing': 0,
            'free': 0,
            'ref': 0,
            'ref1': 0
        }

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
                true_text = "✅ фотография обработана."
                bot.send_photo(int(items[1]), photo, caption=true_text)
            elif items[0] == '/false':
                false_text = "❌ Ваша фотография не подходит! Выберите другое."
                bot.send_photo(int(items[1]), photo, caption=false_text)
                deduct_processing(int(items[1]))  # Вычет обработки из базы данных
            else:
                bot.reply_to(message, "Неверный формат команды.")
        else:
            bot.reply_to(message, "Подпись к фото отсутствует.")



# Функция вычета обработки из базы данных
def deduct_processing(user_id):
    if user_id in users_processing:
       users_processing[user_id]['count_processing'] += 1
       with open('data.yml', 'w') as file:
           yaml.safe_dump(users_processing, file)
    else:
       bot.send_message(user_id, "Требуется перезагрузка - /start")



@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id

    if user_id not in users_processing:
        # Проверяем, есть ли параметр в команде
        if message.text.startswith('/start'):
            start_param = message.text.split(' ')[1] if len(message.text.split(' ')) > 1 else None
        
            # Если есть параметр и он является числом, обрабатываем как реферальную ссылку
            if start_param and start_param.isdigit():
                referred_by = int(start_param)
                
        agreement_text = (
            '🔞 Вам необходимо ознакомиться с пользовательским соглашением и подтвердить, что Вам уже исполнилось 18 лет.\n\n'
            '✅ Кнопка "Я согласен" подтверждает ваше согласие с вышеперечисленным.\n\n'
            'https://telegra.ph/Polzovatelskoe-soglashenie-SnapNudify-08-29'
        )
        agreement_button = types.InlineKeyboardButton('✅ Я согласен', callback_data=f'agreed {referred_by}')
        agreement_keyboard = types.InlineKeyboardMarkup().add(agreement_button)

        bot.send_message(user_id, agreement_text, reply_markup=agreement_keyboard, parse_mode='Markdown', disable_web_page_preview=True)
    else:
        send_main_keyboard(user_id)

# Обработчик для кнопки реферальной системы
@bot.message_handler(func=lambda message: message.text == '💸 Реферальная система')
def referral_system(message):
    user_id = message.from_user.id
    user_referrals = users_processing.get(user_id, {}).get('ref', 0)
    referrals_until_free = 5 - users_processing.get(user_id, {}).get('ref1', 0)

    referral_message = (
        f"👥 Рефералы: <b>{user_referrals}</b>\n"
        f"♻️ До бесплатной обработки еще нужно <b>{referrals_until_free}</b> рефералов\n\n"
        f"<b>Ссылка для приглашения:</b> \n<code>https://t.me/{bot.get_me().username}?start={user_id}</code>\n\n"
        f"🤝 <b>Вы будете получать одну бесплатную обработку за каждых 5 новых пользователей зарегистрированных по вашей реферальной ссылке.</b>", 
    )

    bot.send_message(user_id, referral_message, parse_mode='HTML')

# Обработчик для кнопки согласия
@bot.callback_query_handler(func=lambda call: call.data.startswith('agreed'))
def agreed_callback(call):
    user_id = call.from_user.id
    if user_id not in users_processing:
        # Пользователя нет в базе данных, записываем его
        users_processing[user_id] = {
            'user_name': bot.get_chat(user_id).username,
            'count_processing': 0,
            'free': 1,
            'ref': 0,
            'ref1': 0
        }

        # Извлекаем user_id из callback_data
        referred_by = int(call.data.split(' ')[1])

        if referred_by in users_processing:
            users_processing[referred_by]['ref'] += 1
            users_processing[referred_by]['ref1'] += 1
            referrals_until_free = 5 - users_processing[referred_by]['ref1']
            with open('data.yml', 'w') as file:
                yaml.safe_dump(users_processing, file)
            bot.send_message(referred_by, parse_mode='HTML', text=f"👤 Новый реферал!\n\n🏠 У вас <b>{users_processing[referred_by]['ref']}</b> рефералов.\n♻️ До обработки <b>{referrals_until_free}</b> рефералов.")
            if users_processing[referred_by]['ref1'] == 5:
                users_processing[referred_by]['ref1'] = 0
                users_processing[referred_by]['count_processing'] += 1
                bot.send_message(referred_by, parse_mode='HTML', text=f"✅ Получено <b>1</b> обработка.\n🏠 У вас: <b>{users_processing[referred_by]['count_processing']}</b> обработок")

                save_data()

    with open('data.yml', 'a') as file:
        file.write(f'\n- user_id: {user_id}\n user_name: {users_processing[user_id]["user_name"]}\n count_processing: {users_processing[user_id]["count_processing"]}\n free: {users_processing[user_id]["free"]}\n ref: {users_processing[user_id]["ref"]}\n ref1: {users_processing[user_id]["ref1"]}')

    send_main_keyboard(user_id)  # Отправляем главное меню
    save_data()
    
# Функция для отправки главного меню
def send_main_keyboard(user_id):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton('🔞 Раздеть девушку')
    button2 = types.KeyboardButton('🛒 Купить обработки')
    button3 = types.KeyboardButton('💼 Профиль')
    button4 = types.KeyboardButton('📃 Инструкция')
    ref = types.KeyboardButton('💸 Реферальная система')
    support_button = types.KeyboardButton('🛠️ Тех.Поддержка')
    
    keyboard.add(button1, button3)
    keyboard.add(button2, button4)
    keyboard.add(ref)
    keyboard.add(support_button)
    
    
    inline_button = types.InlineKeyboardButton('📷 Показать примеры', url='https://telegra.ph/SnapNudify-Primery-08-29')
    inline_keyboard = types.InlineKeyboardMarkup().add(inline_button)
    
    start_photo = open('start.jpg', 'rb')
    
    text = "👋"
    caption = (f"<b>🤖 Я - нейросеть, которая раздевает фото любой девушки.</b>\n\n"
              f"<b>📷 Просто отправьте боту фото на котором изображена девушка!</b>\n\n"
              f"👇 Обязательно посмотри примеры обработок.\n\n"
    )
    bot.send_message(user_id, text, reply_markup=keyboard)
    bot.send_photo(user_id, photo=start_photo, caption=caption, reply_markup=inline_keyboard, parse_mode='HTML')
    
    save_data()



@bot.message_handler(func=lambda message: message.text == '📃 Инструкция')
def send_instructions(message):
    user_id = message.from_user.id
    if user_id not in users_processing:
        users_processing[user_id] = {
            'user_name': bot.get_chat(user_id).username,
            'count_processing': 0,
            'free': 0,
            'ref': 0,
            'ref1': 0
        }

    instructions = (f"<b>🗓 Инструкция:</b>\n\n"
              f"<b>🔶 Девушка на фото должна быть повернута передом, стоять прямо в ествественной позе с прямым ракурсом. Обязательно перед заказом обработки посмотрите пример обработанных фотографий.</b>\n\n"
              f"<b>🔶 Фотография обрабатываеться среднем в течении 1 минуты, время орбаботки зависит от нагруженности бота. Уточнить время обработки после заказа обработки всегда можно у Тех.Поддержки</b>\n\n"
              f"<b>🔶 Если вашу фотографию обработать не получилось, бот отменит обрбаотку. Если вы хотите отменить ещё не выполненный заказ то пишете в Тех.Поддержку</b>\n\n"
              f"<b>🔶 Мы не несем отвесвенность за плохой результат обработки.</b>\n\n\n"
              f"<b>📨 С вопросами можете обратиться сюда - @snapnudify_support</b>"
    )
    # Создание инлайн-кнопки и добавление её к сообщению с инструкциями
    inline_button = types.InlineKeyboardButton('🛠️ Тех.Поддержка', url='https://t.me/snapnudify_support')
    inline_keyboard = types.InlineKeyboardMarkup()
    inline_keyboard.add(inline_button)

    bot.send_message(message.chat.id, instructions, parse_mode='HTML', reply_markup=inline_keyboard)

    # Сохранение данных в файл
    save_data()

@bot.message_handler(func=lambda message: message.text == '🛠️ Тех.Поддержка')
def support(message):
    inline_button = types.InlineKeyboardButton('🛠️ Тех.Поддержка', url='https://t.me/snapnudify_support')
    inline_keyboard = types.InlineKeyboardMarkup()
    inline_keyboard.add(inline_button)
    bot.send_message(message.chat.id, f"<b>📨 С вопросами можете обратиться сюда - @snapnudify_support</b>", parse_mode='HTML', reply_markup=inline_keyboard)
    
# Обработчик нажатия на кнопку "Купить обработку"
@bot.message_handler(func=lambda message: message.text == '🛒 Купить обработки')
def buy_processing(message):
    user_id = message.from_user.id
    if user_id not in users_processing:
        users_processing[user_id] = {
            'user_name': bot.get_chat(user_id).username,
            'count_processing': 0,
            'free': 0,
            'ref': 0,
            'ref1': 0
        }

        # Добавление нового пользователя в файл
        with open('data.yml', 'a') as file:
            file.write(f'\n- user_id: {user_id}\n user_name: {users_processing[user_id]["user_name"]}\n count_processing: {users_processing[user_id]["count_processing"]}\n free: {users_processing[user_id]["free"]}\n ref: {users_processing[user_id]["ref"]}\n ref1: {users_processing[user_id]["ref1"]}')

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

    count_processing = users_processing[user_id]['count_processing']
    free_processing = users_processing[user_id]['free']  # Получаем количество бесплатных обработок
    message_text = f"Количество обработок: {count_processing}\n\n<b>Выберите тариф:</b>"
    bot.send_message(message.chat.id, text=message_text, reply_markup=keyboard, parse_mode='HTML')

    # Сохранение данных в файл
    save_data()


# Обработчик нажатия на кнопку "💼 Профиль"
@bot.message_handler(func=lambda message: message.text == '💼 Профиль')
def show_profile(message):
    user_id = message.from_user.id
    if user_id in users_processing:
        inline_button_1 = types.InlineKeyboardButton('Пользовательское соглашение', url='https://telegra.ph/Polzovatelskoe-soglashenie-SnapNudify-08-29')
        inline_button_2 = types.InlineKeyboardButton('Политика конфиденциальности', url='https://telegra.ph/Politika-konfidencialnosti-dlya-bota-razdip-bot-08-27')
        inline_keyboard = types.InlineKeyboardMarkup()
        inline_keyboard.add(inline_button_1)
        inline_keyboard.add(inline_button_2)
        user_name = users_processing[user_id]['user_name']
        count_processing = users_processing[user_id]['count_processing']
    
        # Формирование текста профиля
        profile_text = f"🏠 ID: <code>{user_id}</code>\n👑 Количество обработок: <b>{count_processing}</b>"
        profile_text += f"\n\n🌐 Тех.Поддержка - @snapnudify_support"

        # Отправка сообщения с профилем пользователя
        bot.send_message(message.chat.id, profile_text, parse_mode='HTML', disable_web_page_preview=True, reply_markup=inline_keyboard)
    else:
        # Если пользователя нет в базе данных, добавляем его с информацией по умолчанию
        user_name = message.from_user.username
        users_processing[user_id] = {
            'user_name': user_name,
            'count_processing': 0,
            'free': 0,
            'ref': 0,
            'ref1': 0
        }

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
        free_processing = users_processing[user_id]['free']  # Получаем количество бесплатных обработок

        if count_processing > 0 or free_processing > 0:  # Изменено условие
            bot.send_message(message.chat.id, "<b>Отправьте фото:</b>", parse_mode='HTML')
        else:
            keyboard = types.InlineKeyboardMarkup()
            button = types.InlineKeyboardButton('🛒 Купить обработку', callback_data='buy_processing')
            keyboard.add(button)
            insufficient_message = bot.send_message(message.chat.id, "⛔ У вас недостаточно обработок. Чтобы купить обработки, нажмите на кнопку ниже 👇", reply_markup=keyboard, parse_mode='HTML')

    else:
        user_name = message.from_user.username
        users_processing[user_id] = {
            'user_name': user_name,
            'count_processing': 0,
            'free': 0,
            'ref': 0,
            'ref1': 0
        }

        # Записываем обновленные данные в файл data.yml
        save_user_data(users_processing)

        request_photo(message)

# Обработчик нажатия на кнопку "Купить обработку"
@bot.callback_query_handler(func=lambda call: call.data == 'buy_processing')
def handle_buy_processing(call):
    user_id = call.from_user.id
    # Логика обработки нажатия на кнопку "Купить обработку"
    if user_id not in users_processing:
        users_processing[user_id] = {
            'user_name': bot.get_chat(user_id).username,
            'count_processing': 0,
            'free': 0,
            'ref': 0,
            'ref1': 0
        }

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
                bot.send_message(message.chat.id, "Требуется перезагрузка - /start")
        else:
            bot.send_message(message.chat.id, "Неверный формат команды. Используйте /info <user_id>")
    else:
        bot.send_message(message.chat.id, "У вас нет доступа к этой команде.")


# Функция проверки статуса платежа в отдельном потоке
def check_payment_status_thread(token, label, user_id, count_processing, payment_message, payment_message_id):
    if check_payment_status(token, label):
        # Начисление обработок и отправка сообщения об успешной оплате
        users_processing[user_id]['count_processing'] += count_processing
        send_payment_success_message(user_id, count_processing)
        bot.delete_message(chat_id=user_id, message_id=payment_message_id)
        print("Платеж успешный")
    else:
        bot.send_message(user_id, "Платеж неуспешный. Пожалуйста, попробуйте еще раз.")
        bot.delete_message(chat_id=user_id, message_id=payment_message_id)
        print("Платеж неуспешный")


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
                bot.delete_message(call.message.chat.id, call.message.message_id)
                payment_message = bot.send_message(user_id, message_text, reply_markup=keyboard, parse_mode='HTML')
                payment_message_id = payment_message.message_id


                # Проверка успешности платежа в отдельном потоке
                payment_status_thread = threading.Thread(target=check_payment_status_thread, args=(token, label, user_id, count_processing, payment_message, payment_message_id))
                payment_status_thread.start()
            else:
                bot.send_message(user_id, "Ошибка при создании платежа. Пожалуйста, попробуйте еще раз.")
        else:
            bot.send_message(user_id, "Выбран неправильный тариф. Пожалуйста, повторите выбор.")
    elif call.data == 'other_payment':
        # Создание инлайн-кнопки и добавление ее к сообщению с инструкциями
        inline = types.InlineKeyboardMarkup()
        inline_button = types.InlineKeyboardButton('♻ Тех.Поддержка', url='https://t.me/snapnudify_support')
        inline.add(inline_button)
        bot.send_message(user_id, "🔗 Для оплаты другими сервисами свяжитесь с Тех.Поддержкой - @snapnudify_support", reply_markup=inline)
        bot.delete_message(call.message.chat.id, call.message.message_id)


# Запуск бота
while True:
  try:
    bot.polling(none_stop=True)
  except Exception as e:
    print(f"Ошибка в цикле: {e}")
    time.sleep(15) 
