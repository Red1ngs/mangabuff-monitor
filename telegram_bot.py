import requests
from datetime import datetime

class TelegramNotifier:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
    
    def send_photo(self, photo_url, caption, parse_mode="HTML"):
        """Отправка фото с подписью"""
        try:
            url = f"{self.api_url}/sendPhoto"
            
            # Добавляем https:// если нужно
            if photo_url and photo_url.startswith('/'):
                photo_url = f"https://mangabuff.ru{photo_url}"
            
            data = {
                "chat_id": self.chat_id,
                "photo": photo_url,
                "caption": caption,
                "parse_mode": parse_mode
            }
            
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Уведомление отправлено")
                return True
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Ошибка: {response.text}")
                return False
                
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Ошибка отправки: {e}")
            return False
    
    def send_message(self, text, parse_mode="HTML"):
        """Отправка текстового сообщения"""
        try:
            url = f"{self.api_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode
            }
            
            response = requests.post(url, data=data, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")
            return False
    
    def format_manga_notification(self, manga_info):
        """Форматирование уведомления о манге"""
        
        # Используем <code> для копируемого названия
        caption = f"""🔔 <b>Смена тайтла в альянсе!</b>

📚 <code>{manga_info['title']}</code>

🔗 <a href="https://mangabuff.ru/alliances/10/boost">Перейти к вкладке альянса</a>

⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"""
        
        return caption