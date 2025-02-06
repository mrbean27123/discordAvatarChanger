import os
import ctypes
import base64
import random
import psutil
import time

from tls_client import Session
from loguru import logger
from datetime import datetime, date

from settings import settings

session = Session(client_identifier="chrome_115", random_tls_extension_order=True)

headers = {
    "authority": "discord.com",
    "method": "PATCH",
    "scheme": "https",
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": "en-US",
    "authorization": settings.DISCORD_TOKEN,
    "origin": "https://discord.com",
    "sec-ch-ua": '"Not/A)Brand";v="99", "Brave";v="115", "Chromium";v="115"',
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9020 Chrome/108.0.5359.215 Electron/22.3.26 Safari/537.36",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "X-Debug-Options": "bugReporterEnabled",
    "X-Discord-Locale": "en-US",
    "X-Discord-Timezone": "Asia/Calcutta",
    "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiRGlzY29yZCBDbGllbnQiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfdmVyc2lvbiI6IjEuMC45MDIwIiwib3NfdmVyc2lvbiI6IjEwLjAuMTkwNDUiLCJvc19hcmNoIjoieDY0IiwiYXBwX2FyY2giOiJpYTMyIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV09XNjQpIEFwcGxlV2ViS2l0LzUzNy4zNiAoS0hUTUwsIGxpa2UgR2Vja28pIGRpc2NvcmQvMS4wLjkwMjAgQ2hyb21lLzEwOC4wLjUzNTkuMjE1IEVsZWN0cm9uLzIyLjMuMjYgU2FmYXJpLzUzNy4zNiIsImJyb3dzZXJfdmVyc2lvbiI6IjIyLjMuMjYiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjoyNDAyMzcsIm5hdGl2ZV9idWlsZF9udW1iZXIiOjM4NTE3LCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsLCJkZXNpZ25faWQiOjB9"
}


def extract_errors(errors):
    """Рекурсивно извлекает все сообщения об ошибках из JSON-ответа."""
    messages = []

    if isinstance(errors, dict):
        for key, value in errors.items():
            messages.extend(extract_errors(value))

    elif isinstance(errors, list):
        for item in errors:
            messages.extend(extract_errors(item))

    elif isinstance(errors, str):
        messages.append(errors)

    return messages


def is_discord_running():
    for process in psutil.process_iter(attrs=['name']):
        if settings.DISCORD_PROCESS == process.info['name'].lower():
            return True
    return False


def get_images(folder_path):
    # Проверяем, существует ли папка
    if not os.path.exists(folder_path):
        # Если папки нет, создаём её
        ctypes.windll.user32.MessageBoxW(0, "Введите в settings.ini путь к папке с изображениями в IMAGE_PATH", settings.TITLE, 16)
        raise SystemExit("")
    # Фильтруем только изображения по расширениям
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    images = [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if os.path.splitext(f)[1].lower() in image_extensions
    ]
    if not images:
        ctypes.windll.user32.MessageBoxW(0,"Изображений не найдено", settings.TITLE, 16)
        raise SystemExit("")
    return images


def get_user_data():
    r = session.patch("https://discord.com/api/v9/users/@me", headers=headers)
    if r.status_code == 200:
        return r.json()
    else:
        return None


def change_avatar(image_path):
    payload = {"avatar": f"data:image/jpeg;base64,{base64.b64encode(open(image_path, 'rb').read()).decode()}"}
    r = session.patch("https://discord.com/api/v9/users/@me", json=payload, headers=headers)
    all_error_messages = extract_errors(errors=r.json())
    error_text = ": ".join(all_error_messages)
    while "Unknown Session" in error_text or "You are changing your avatar too fast" in error_text:
        if r.status_code == 200:
            settings.update_settings("current_avatar", image_path)
            settings.update_settings("last_update", f"{date.today()}")
            logger.success("Аватар успешно изменен")
            raise SystemExit("")
        else:
            logger.error(f"Код: {r.status_code} Ошибка: {error_text}")
            time.sleep(15)
            r = session.patch("https://discord.com/api/v9/users/@me", json=payload, headers=headers)
            all_error_messages = extract_errors(errors=r.json())
            error_text = ": ".join(all_error_messages)
    if r.status_code == 200:
        settings.update_settings("current_avatar", image_path)
        settings.update_settings("last_update", f"{date.today()}")
        logger.success("Аватар успешно изменен")
    elif r.status_code == 401 and "Unauthorized" in error_text:
        logger.error(f"Код: {r.status_code} Ошибка: {error_text}")
        ctypes.windll.user32.MessageBoxW(
            0,
            f"Ошибка авторизации. Проверьте правильность токена\n\n{error_text}",
            f"{settings.TITLE} {r.status_code}",
            16
        )
    else:
        logger.error(f"Код: {r.status_code} Ошибка: {error_text}")
        ctypes.windll.user32.MessageBoxW(
            0,
            f"{error_text}",
            f"{settings.TITLE} {r.status_code}",
            16
        )


def random_image_not_current(images):
    if settings.current_avatar in images:
        images.remove(settings.current_avatar)
    random_image = random.choice(images)
    return random_image


def main():
    if settings.UPDATE_ONCE_A_DAY is True and settings.last_update is not None and date.today() == datetime.strptime(settings.last_update, "%Y-%m-%d").date():
        logger.info("Сегодня аватарка уже изменялась")
        raise SystemExit("")
    discord_status = is_discord_running()
    while not discord_status:
        discord_status = is_discord_running()
        if discord_status:
            logger.debug(f"{settings.DISCORD_PROCESS} запущен")
        else:
            logger.error(f"{settings.DISCORD_PROCESS} не запущен")
            time.sleep(5)
    images = get_images(settings.IMAGE_PATH)
    logger.debug(f"{images=}")
    logger.debug(f"{settings.RANDOM_TYPE=}")
    # Рандомная картинка из списка, но не текущая
    if settings.RANDOM_TYPE == 0:
        random_image = random_image_not_current(images=images)
    # Выбирает имя+1 из текущего списка, после прохода всех ников генерируется рандомный список
    elif settings.RANDOM_TYPE == 1:
        # Если current_image_list не существует, генерируем рандомный список
        if settings.current_image_list is None:
            logger.debug(f"{settings.current_image_list=}")
            settings.update_settings("current_image_list", random.sample(images, len(images)))
            random_image = settings.current_image_list[0]
        else:
            # Если файлы в списке поменялись
            if sorted(images) != sorted(settings.current_image_list):
                logger.debug(f"файлы в списке поменялись\n{images=}\n{settings.current_image_list=}")
                # Получаем элементы из current_image_list которые есть и в images
                new_current_image_list = [x for x in settings.current_image_list if x in images or x == settings.current_avatar]
                # Находим элементы, которых нет current_image_list
                missing_elements = [x for x in images if x not in new_current_image_list]
                # Перемешиваем недостающие элементы
                random.shuffle(missing_elements)
                # Добавляем их в конец списка
                new_current_image_list.extend(missing_elements)
                # Обновляем current_image_list
                settings.update_settings("current_image_list", new_current_image_list)

            index = settings.current_image_list.index(settings.current_avatar)
            all_index = len(settings.current_image_list) - 1
            logger.debug(f"Current index: {index}/{all_index}")

            elements_after = settings.current_image_list[index + 1:]
            if elements_after:
                random_image = elements_after[0]
            # Если элементы после текущего закончились
            else:
                logger.debug(f"Элементы после текущего закончились")
                # Вычисляем средний индекс
                middle_index = len(settings.current_image_list) // 2
                # Разделяем список на две части
                first_half = settings.current_image_list[:middle_index]
                second_half = settings.current_image_list[middle_index:]
                random.shuffle(first_half)
                random.shuffle(second_half)
                new_images = first_half + second_half
                settings.update_settings("current_image_list", new_images)
                random_image = settings.current_image_list[0]
                logger.debug(f"new_list={settings.current_image_list}")
    else:
        logger.debug(f"{settings.RANDOM_TYPE=} не существует")
        ctypes.windll.user32.MessageBoxW(0, f"{settings.RANDOM_TYPE=} не существует", settings.TITLE, 16)
        raise SystemExit("")

    change_avatar(image_path=random_image)


if __name__ == "__main__":
    main()