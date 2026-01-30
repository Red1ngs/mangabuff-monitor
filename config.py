import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # MangaBuff
    MANGABUFF_EMAIL = os.getenv('MANGABUFF_EMAIL')
    MANGABUFF_PASSWORD = os.getenv('MANGABUFF_PASSWORD')
    ALLIANCE_URL = f"https://mangabuff.ru/alliances/{os.getenv('ALLIANCE_ID', '10')}/boost"
    
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    
    # Мониторинг
    CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 1))
    HEADLESS_MODE = os.getenv('HEADLESS_MODE', 'false').lower() == 'true'
    
    # Пути
    HISTORY_FILE = 'manga_history.json'
    LOG_DIR = 'logs'
    LOG_FILE = os.path.join(LOG_DIR, 'monitor.log')
    
    @classmethod
    def validate(cls):
        """Проверка наличия всех необходимых настроек"""
        required = {
            'MANGABUFF_EMAIL': cls.MANGABUFF_EMAIL,
            'MANGABUFF_PASSWORD': cls.MANGABUFF_PASSWORD,
            'TELEGRAM_BOT_TOKEN': cls.TELEGRAM_BOT_TOKEN,
            'TELEGRAM_CHAT_ID': cls.TELEGRAM_CHAT_ID,
        }
        
        missing = [key for key, value in required.items() if not value]
        
        if missing:
            raise ValueError(f"Отсутствуют настройки: {', '.join(missing)}")
        
        return True