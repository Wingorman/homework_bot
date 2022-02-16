from requests.exceptions import RequestException
import logging
import os
import time
import requests
import telegram
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s, %(levelname)s, %(name)s, %(message)s",
    filename="main.log",
)
logger = logging.getLogger(__name__)

load_dotenv()


PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_TIME = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}


HOMEWORK_STATUSES = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}


def send_message(bot, message):
    return bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)


def get_api_answer(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    params = {"from_date": timestamp}
    answer = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
    answer_code = answer.status_code
    if answer_code != requests.codes.ok:
        message = f"Тут сообщение что что-то поломалось"
        raise RequestException(message)
    return answer.json()


def check_response(response):
    """Проверяет ответ API на корректнось."""
    if not isinstance(response, dict):
        raise TypeError
    homework = response.get("homeworks")
    if homework is None:
        raise TypeError
    if not isinstance(homework, list):
        raise TypeError
    return homework


def parse_status(homework):
    homework_name = homework.get("homework_name")
    if homework_name is None:
        raise KeyError
    homework_status = homework.get("status")
    for key, value in HOMEWORK_STATUSES.items():
        if homework_status == key:
            verdict = value
            return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    raise ValueError


def check_tokens():
    tokens = all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])
    if tokens:
        return True
    return False


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        error_message = "Ошибка в токенах!"
        logger.error(error_message)
        raise Exception(error_message)
    last_error = None

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    logger.info("Бот начал работу")

    while True:
        try:
            response = get_api_answer(current_timestamp)
            is_response_ok = check_response(response)
            if is_response_ok:
                send_message(bot, parse_status(is_response_ok[0]))
                logging.info("Сообщение отправлено")
            else:
                logging.debug("Статус загруженных работ не изменился")

            current_timestamp = response.get("current_date", current_timestamp)
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            if last_error != error:
                send_message(bot, message)
            time.sleep(RETRY_TIME)
        else:
            if last_error:
                message = f"Сбой в работе программы"
                logging.info("БОТ ОКОНЧАТЕЛЬНО СЛОМАН")
                send_message(bot, message)
            last_error = None


if __name__ == "__main__":
    main()
