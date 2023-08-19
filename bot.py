import telebot
import os
import subprocess
from PIL import Image, ImageOps
from io import BytesIO
import os, subprocess, time, glob
import webuiapi

token = "6550926108:AAHbCdI05A5S44_cK693jKmyStWlTRwbSuo"
bot = telebot.TeleBot(token)

# Инициализируем API для инпейнтинга
# api = webuiapi.WebUIApi()
api = webuiapi.WebUIApi(host='127.0.0.1',
                        port=7860,
                        sampler='DPM++ SDE',
                        steps=40)
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    file_id = message.photo[-1].file_id

    # Скачиваем фото
    file_path = bot.get_file(file_id).file_path
    downloaded_file = bot.download_file(file_path)

    # Сохраняем фото
    src = '/content/images/' + file_id + '.jpg'
    with open(src, 'wb') as new_file:
        new_file.write(downloaded_file)

    try:
        # Выполняем скрипт для создания маски

        pascal_command  = [
            "python3",
            "/content/ggoolfsdfs23/simple_extractor.py",  # Проверьте путь к скрипту
            "--dataset", "pascal",
            "--model-restore", "pascal/pascal.pth",
            "--input-dir", "images",
            "--output-dir", "pascal_results"
        ]
        subprocess.run(pascal_command)

        lib_command  = [
            "python3",
            "/content/ggoolfsdfs23/simple_extractor.py",  # Проверьте путь к скрипту
            "--dataset", "lip",
            "--model-restore", "lib/lib.pth",
            "--input-dir", "images",
            "--output-dir", "lib_results"
        ]
        subprocess.run(lib_command)
        
        pascal_mask_path = 'pascal_results/' + file_id + '.png'
        lib_mask_path = 'lib_results/' + file_id + '.png'

        pascal_mask = Image.open(pascal_mask_path).convert("L")
        lib_mask = Image.open(lib_mask_path).convert("L")
        

        # Применяем операцию объединения масок
        alpha = 1
        combined_mask = Image.blend(pascal_mask, lib_mask, alpha)

        combined_mask_path = 'results/' + file_id + '.png'
        combined_mask.save(combined_mask_path)

        # Применяем инпейнтинг
        mask_path = combined_mask_path
        result2_path = 'images/' + file_id + '.jpg'  # Путь к вашему result2 изображению

        mask = Image.open(mask_path)
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
            bot.send_photo(message.chat.id, photo=buf)

        # Удаляем файлы
        os.remove(src)
        os.remove(mask_path)
    except subprocess.CalledProcessError as e:
        print("Ошибка при выполнении команды:", e)
        
bot.polling()
