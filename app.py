import datetime
import configparser
import random
import asyncio

from telethon.sync import TelegramClient
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import (
    ChatAdminRequiredError,
    UserAlreadyParticipantError,
    FloodWaitError,
    UserIsBlockedError,
    ChannelPrivateError
)
from telethon import events


# Ваши учетные данные API Telethon
api_id = 20559113
api_hash = 'ed8e97b3a73a324f5cf0b6dae63239b2'

# Путь к текстовому документу с перечисленными именами чатов
chat_list_path = 'chat_list.txt'

# Путь к текстовому документу с сообщением для рассылки
message_path = 'message.txt'

# Путь к файлу с заготовленным сообщением
reply_message_path = 'reply_message.txt'

# Путь к файлу с интервалом задержки перед рассылкой (в секундах)
interval_path = 'interval.txt'


# Функция для вступления в чат по его имени
async def join_chat(client, chat_name):
    try:
        await client(JoinChannelRequest(chat_name))
        print_with_time('🌐 Успешно присоединился к чату:', chat_name)
    except ChatAdminRequiredError:
        pass
    except UserAlreadyParticipantError:
        print_with_time('Вы уже участник чата:', chat_name)
    except FloodWaitError as e:
        print_with_time(f'⏳ Ожидание в течение {e.seconds} секунд')
        await asyncio.sleep(e.seconds)
        await join_chat(client, chat_name)  # Повторная попытка вступления после ожидания
    except UserIsBlockedError:
        print_with_time('Вы заблокированы в чате:', chat_name)
    except ChannelPrivateError:
        print_with_time('⛔ Не удалось присоединиться к чату:', chat_name)


# Функция для отправки заготовленного сообщения без предварительного просмотра
async def send_message_without_preview(event):
    try:
        with open(reply_message_path, 'r', encoding='utf-8') as file:
            message = file.read()
        await event.respond(message, link_preview=False)
        print_with_time('🚹 Ответ успешно отправлен')
        return True
    except Exception as e:
        if 'You can\'t write in this chat' not in str(e):
            print_with_time('❌ Не удалось отправить сообщение:', e)
        return False


# Функция для получения случайного интервала задержки из заданного диапазона
def get_message_interval():
    with open(interval_path, 'r') as file:
        min_interval, max_interval = map(int, file.read().strip().split())
    return random.randint(min_interval, max_interval)


# Асинхронная функция для отправки сообщений в чаты
async def send_messages(client):
    # Читаем сообщение из текстового документа
    with open(message_path, 'r', encoding='utf-8') as file:
        message = file.read()

    # Открываем файл с перечисленными именами чатов
    with open(chat_list_path, 'r') as file:
        # Читаем имена чатов из файла
        chat_names = file.read().splitlines()

        # Присоединяемся к каждому чату по его имени
        for name in chat_names:
            await join_chat(client, name if name.startswith('@') else f'@{name}')

    successful_messages = 0
    total_messages = len(chat_names)

    # Цикличная рассылка сообщения во все чаты с заданным интервалом
    while True:
        for chat_name in chat_names:
            try:
                await client.send_message(chat_name, message)
                print_with_time('✅ Сообщение успешно отправлено в чат:', chat_name)
                successful_messages += 1
            except ChatAdminRequiredError:
                pass
            except UserAlreadyParticipantError:
                print_with_time('Вы уже участник чата:', chat_name)
            except FloodWaitError as e:
                print_with_time('⏳ Ожидание в течение', e.seconds, 'секунд')
                await asyncio.sleep(e.seconds)
                continue
            except UserIsBlockedError:
                print_with_time('Вы заблокированы в чате:', chat_name)
            except ChannelPrivateError:
                print_with_time('❌ Не удалось отправить сообщение:', chat_name)
            except Exception as e:
                if 'You can\'t write in this chat' not in str(e):
                    print_with_time('❌ Не удалось отправить сообщение в чат:', chat_name)
                    print(e)

        interval = get_message_interval()
        print_with_time(f'♻️ Отправлено {successful_messages} сообщений ♻️')
        print_with_time('🕒 Следующая отправка через', interval, 'секунд')
        await asyncio.sleep(interval)


# Создаем клиента Telegram
client = TelegramClient('telethon', api_id, api_hash)


# Запускаем клиента Telegram
async def run_client():
    async with client:
        # Устанавливаем новую информацию о себе
        await client(UpdateProfileRequest(first_name='СМОТРИ', last_name='ПРОФИЛЬ'))
        # Устанавливаем новую информацию о себе
        await client(UpdateProfileRequest(about='Бот 👉 t.me/snapnudify_bot t.me/snapnudify_bot'))

        # Обрабатываем входящие сообщения
        @client.on(events.NewMessage)
        async def handler(event):
            if event.is_private:
                await send_message_without_preview(event)

        # Запускаем цикл отправки сообщений
        await send_messages(client)


# Функция для вывода сообщений с временной меткой
def print_with_time(message, *args):
    current_time = datetime.datetime.now().strftime("%H:%M")
    print(f"[{current_time}] {message}", *args)


# Запускаем асинхронный цикл событий
loop = asyncio.get_event_loop()
loop.run_until_complete(run_client())