import time
import json
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup

from config import Config
from telegram_bot import TelegramNotifier


class MangaBuffMonitor:
    def __init__(self):
        self.config = Config()
        self.telegram = TelegramNotifier(
            self.config.TELEGRAM_BOT_TOKEN,
            self.config.TELEGRAM_CHAT_ID
        )
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.current_manga = None
        
        # Создаем папку для логов
        os.makedirs(self.config.LOG_DIR, exist_ok=True)
    
    def log(self, message, force=False):
        """Логирование с поддержкой quiet режима"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        
        # Всегда выводим в консоль
        print(log_message)
        
        # В файл пишем только важные сообщения или принудительно
        if force or any(marker in message for marker in ['✅', '❌', '🔔', '⚠️', '🔐', '🚀', '⏹️']):
            with open(self.config.LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(log_message + '\n')
    
    def login(self):
        """Авторизация через requests"""
        try:
            self.log("🔐 Вход в аккаунт...")
            
            # Получаем главную страницу для получения cookies
            response = self.session.get("https://mangabuff.ru", timeout=10)
            
            if response.status_code != 200:
                self.log(f"❌ Ошибка получения главной страницы: {response.status_code}")
                return False
            
            # Получаем CSRF токен если есть
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_token = None
            
            # Ищем CSRF токен в мета-тегах
            csrf_meta = soup.find('meta', {'name': 'csrf-token'})
            if csrf_meta:
                csrf_token = csrf_meta.get('content')
            
            # Подготавливаем данные для входа
            login_data = {
                'email': self.config.MANGABUFF_EMAIL,
                'password': self.config.MANGABUFF_PASSWORD,
            }
            
            if csrf_token:
                login_data['_token'] = csrf_token
            
            # Отправляем запрос на авторизацию
            login_response = self.session.post(
                "https://mangabuff.ru/login",
                data=login_data,
                timeout=10,
                allow_redirects=True
            )
            
            # Проверяем успешность входа
            if login_response.status_code == 200:
                # Проверяем, есть ли признаки успешной авторизации
                check_response = self.session.get("https://mangabuff.ru", timeout=10)
                soup_check = BeautifulSoup(check_response.text, 'html.parser')
                
                # Ищем элементы, которые появляются только у авторизованных пользователей
                profile = soup_check.find('div', class_='header-profile')
                
                if profile:
                    self.log("✅ Успешный вход")
                    return True
                else:
                    self.log("❌ Не удалось войти - проверьте email и пароль")
                    return False
            else:
                self.log(f"❌ Ошибка входа: {login_response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ Ошибка при входе: {e}")
            return False
    
    def get_current_manga_slug(self):
        """Получение slug текущей манги из страницы альянса с retry"""
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(self.config.ALLIANCE_URL, timeout=15)
                
                # Обработка ошибок сервера
                if response.status_code == 500:
                    self.log(f"⚠️ Ошибка сервера 500 (попытка {attempt + 1}/{max_retries})", force=True)
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return None
                
                if response.status_code != 200:
                    self.log(f"⚠️ Ошибка получения страницы альянса: {response.status_code}", force=True)
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return None
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Ищем ссылку на мангу
                manga_link = soup.find('a', class_='card-show__placeholder')
                
                if manga_link:
                    href = manga_link.get('href', '')
                    if href and href.startswith('/manga/'):
                        manga_slug = href.replace('/manga/', '')
                        return manga_slug
                
                # Альтернативный метод через постер
                poster = soup.find('div', class_='card-show__header')
                if poster:
                    style = poster.get('style', '')
                    if 'background-image: url(' in style:
                        img_url = style.split("url('")[1].split("'")[0]
                        manga_slug = img_url.split('/posters/')[-1].replace('.jpg', '')
                        return manga_slug
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return None
                
            except requests.exceptions.Timeout:
                self.log(f"⚠️ Таймаут запроса (попытка {attempt + 1}/{max_retries})", force=True)
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return None
                
            except requests.exceptions.ConnectionError:
                self.log(f"⚠️ Ошибка соединения (попытка {attempt + 1}/{max_retries})", force=True)
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return None
                
            except Exception as e:
                self.log(f"⚠️ Ошибка получения slug: {e}", force=True)
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return None
        
        return None
    

    def get_manga_details(self, manga_slug):
        """Получение детальной информации о манге со страницы манги с retry"""
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                url = f"https://mangabuff.ru/manga/{manga_slug}"
                
                response = self.session.get(url, timeout=15)
                
                # Обработка ошибок сервера
                if response.status_code == 500:
                    self.log(f"⚠️ Ошибка сервера 500 при получении деталей (попытка {attempt + 1}/{max_retries})", force=True)
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return None
                
                if response.status_code != 200:
                    self.log(f"❌ Ошибка получения страницы манги: {response.status_code}", force=True)
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return None
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Название манги
                title = None
                
                # Вариант 1: мобильная версия
                title_elem = soup.find('h1', class_='manga-mobile__name')
                if title_elem:
                    title = title_elem.text.strip()
                
                # Вариант 2: десктопная версия
                if not title:
                    title_elem = soup.find('h1', class_='manga__name')
                    if title_elem:
                        title = title_elem.text.strip()
                
                # Если не нашли - используем slug
                if not title:
                    title = manga_slug
                
                # Изображение постера
                img_src = None
                
                # Вариант 1: мобильная версия
                img_elem = soup.find('img', class_='manga-mobile__image')
                if img_elem:
                    img_src = img_elem.get('src')
                
                # Вариант 2: десктопная версия
                if not img_src:
                    img_wrapper = soup.find('div', class_='manga__img')
                    if img_wrapper:
                        img_elem = img_wrapper.find('img')
                        if img_elem:
                            img_src = img_elem.get('src')
                
                # Добавляем домен если путь относительный
                if img_src and img_src.startswith('/'):
                    img_src = f"https://mangabuff.ru{img_src}"
                
                self.log(f"✅ Получены детали: {title}", force=True)
                
                manga_info = {
                    'slug': manga_slug,
                    'title': title,
                    'image': img_src,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                return manga_info
                
            except requests.exceptions.Timeout:
                self.log(f"⚠️ Таймаут при получении деталей (попытка {attempt + 1}/{max_retries})", force=True)
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return None
                
            except requests.exceptions.ConnectionError:
                self.log(f"⚠️ Ошибка соединения при получении деталей (попытка {attempt + 1}/{max_retries})", force=True)
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return None
                
            except Exception as e:
                self.log(f"❌ Ошибка получения деталей: {e}", force=True)
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return None
        
        return None
    
    def save_history(self, manga_info):
        """Сохранение истории изменений в JSON файл"""
        try:
            # Пытаемся загрузить существующую историю
            try:
                with open(self.config.HISTORY_FILE, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except FileNotFoundError:
                history = []
            except json.JSONDecodeError:
                self.log("⚠️ Файл истории поврежден, создаю новый")
                history = []
            
            # Добавляем новую запись
            history.append(manga_info)
            
            # Ограничиваем историю последними 100 записями
            if len(history) > 100:
                history = history[-100:]
            
            # Сохраняем обновленную историю
            with open(self.config.HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            
            self.log(f"💾 История сохранена ({len(history)} записей)")
                
        except Exception as e:
            self.log(f"⚠️ Ошибка сохранения истории: {e}")
    
    def start(self):
        """Запуск мониторинга"""
        try:
            # Проверка настроек
            self.log("🔧 Проверка конфигурации...")
            self.config.validate()
            
            # Авторизация
            if not self.login():
                self.log("❌ Не удалось авторизоваться. Проверьте настройки в .env")
                return
            
            # Получаем начальный тайтл
            self.log("📚 Получаю текущий тайтл альянса...")
            self.current_manga = self.get_current_manga_slug()
            
            if self.current_manga:
                self.log(f"📚 Текущий тайтл: {self.current_manga}")
                
                # Получаем и отправляем информацию о текущем тайтле
                manga_info = self.get_manga_details(self.current_manga)
                if manga_info:
                    caption = self.telegram.format_manga_notification(manga_info)
                    caption = f"🚀 <b>Мониторинг запущен</b>\n\n" + caption
                    
                    if manga_info['image']:
                        self.telegram.send_photo(manga_info['image'], caption)
                    else:
                        self.telegram.send_message(caption)
            else:
                self.log("⚠️ Не удалось получить текущий тайтл")
                self.telegram.send_message("⚠️ Не удалось получить текущий тайтл альянса")
            
            self.log(f"👀 Интервал проверки: {self.config.CHECK_INTERVAL} сек", force=True)
            self.log("🔄 Мониторинг начат. Нажмите Ctrl+C для остановки.", force=True)
            self.log("📊 Логируется каждая 60-я проверка или смена тайтла", force=True)
            
            # Основной цикл мониторинга
            check_count = 0
            while True:
                try:
                    check_count += 1
                    
                    # Логируем каждую 60-ю проверку
                    if check_count % 60 == 0:
                        self.log(f"🔍 Проверка #{check_count}... (тайтл: {self.current_manga})", force=True)
                    else:
                        # Тихая проверка - только в консоль
                        print(f"\r🔍 Проверка #{check_count}... ", end='', flush=True)
                    
                    new_manga = self.get_current_manga_slug()
                    
                    if new_manga:
                        if new_manga != self.current_manga:
                            print()  # Переход на новую строку
                            self.log(f"\n🔔 СМЕНА ТАЙТЛА ОБНАРУЖЕНА!", force=True)
                            self.log(f"   Старый: {self.current_manga}", force=True)
                            self.log(f"   Новый: {new_manga}", force=True)
                            
                            # Получаем детали новой манги
                            manga_info = self.get_manga_details(new_manga)
                            
                            if manga_info:
                                # Отправляем уведомление в Telegram
                                caption = self.telegram.format_manga_notification(manga_info)
                                
                                if manga_info['image']:
                                    self.telegram.send_photo(manga_info['image'], caption)
                                else:
                                    self.telegram.send_message(caption)
                                
                                # Сохраняем в историю
                                self.save_history(manga_info)
                                
                                # Обновляем текущий тайтл
                                self.current_manga = new_manga
                                
                                self.log(f"✅ Уведомление отправлено успешно", force=True)
                            else:
                                self.log("⚠️ Не удалось получить детали новой манги", force=True)
                                self.telegram.send_message(
                                    f"🔔 <b>Смена тайтла!</b>\n\n"
                                    f"Новый тайтл: {new_manga}\n"
                                    f"(не удалось получить детали)"
                                )
                                self.current_manga = new_manga
                        else:
                            # Тайтл не изменился - логируем только каждую 60-ю
                            if check_count % 60 == 0:
                                pass  # Уже залогировано выше
                    else:
                        if check_count % 60 == 0 or check_count == 1:
                            self.log("⚠️ Не удалось получить slug манги", force=True)
                    
                    # Ждем перед следующей проверкой
                    time.sleep(self.config.CHECK_INTERVAL)
                    
                except KeyboardInterrupt:
                    self.log("\n⏹️ Получен сигнал остановки...")
                    self.telegram.send_message("⏹️ Мониторинг остановлен")
                    break
                    
                except requests.exceptions.RequestException as e:
                    self.log(f"⚠️ Ошибка сети: {e}")
                    self.log("🔄 Повторная попытка через 30 секунд...")
                    time.sleep(30)
                    
                    # Пробуем переавторизоваться
                    self.log("🔐 Попытка переавторизации...")
                    if not self.login():
                        self.log("❌ Не удалось переавторизоваться")
                        self.telegram.send_message("❌ Ошибка сети. Мониторинг остановлен.")
                        break
                    
                except Exception as e:
                    self.log(f"⚠️ Непредвиденная ошибка: {e}")
                    import traceback
                    self.log(f"Traceback: {traceback.format_exc()}")
                    time.sleep(5)
                    
        except ValueError as e:
            self.log(f"❌ Ошибка конфигурации: {e}")
            self.log("💡 Проверьте файл .env и убедитесь, что все параметры заполнены")
            
        except Exception as e:
            self.log(f"❌ Критическая ошибка: {e}")
            import traceback
            self.log(f"Traceback: {traceback.format_exc()}")
            
        finally:
            self.log("✅ Мониторинг завершен")