import requests
from datetime import datetime


# Темы для рассылки.
# None = General (message_thread_id не передаётся)
# int  = конкретная тема по ID
TOPIC_IDS = [None, 2280]


class TelegramNotifier:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"

        # Хранит message_id последнего отправленного сообщения для каждой темы
        # Ключ: topic_id (None или int), значение: message_id
        self.active_message_ids: dict = {}

    # ------------------------------------------------------------------
    # Низкоуровневые методы
    # ------------------------------------------------------------------

    def _send_photo(self, photo_url, caption, parse_mode="HTML", message_thread_id=None):
        """Отправляет фото, возвращает message_id или None."""
        try:
            if photo_url and photo_url.startswith('/'):
                photo_url = f"https://mangabuff.ru{photo_url}"

            data = {
                "chat_id": self.chat_id,
                "photo": photo_url,
                "caption": caption,
                "parse_mode": parse_mode,
            }
            if message_thread_id is not None:
                data["message_thread_id"] = message_thread_id

            response = requests.post(f"{self.api_url}/sendPhoto", data=data, timeout=10)
            label = f"тема {message_thread_id}" if message_thread_id is not None else "General"

            if response.status_code == 200:
                msg_id = response.json().get("result", {}).get("message_id")
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Фото отправлено ({label}), msg_id={msg_id}")
                return msg_id
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ sendPhoto ({label}): {response.text}")
                return None

        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Ошибка отправки фото: {e}")
            return None

    def _send_message(self, text, parse_mode="HTML", message_thread_id=None):
        """Отправляет текстовое сообщение, возвращает message_id или None."""
        try:
            data = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
            }
            if message_thread_id is not None:
                data["message_thread_id"] = message_thread_id

            response = requests.post(f"{self.api_url}/sendMessage", data=data, timeout=10)
            if response.status_code == 200:
                return response.json().get("result", {}).get("message_id")
            return None

        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")
            return None

    def _edit_caption(self, message_id, caption, parse_mode="HTML"):
        """Редактирует подпись к фото (тихо, без уведомления)."""
        try:
            data = {
                "chat_id": self.chat_id,
                "message_id": message_id,
                "caption": caption,
                "parse_mode": parse_mode,
            }
            response = requests.post(f"{self.api_url}/editMessageCaption", data=data, timeout=10)
            if response.status_code == 200:
                return True
            else:
                # Если подпись не изменилась — Telegram вернёт ошибку "message is not modified"
                # Это нормально, не считаем за ошибку
                err = response.json().get("description", "")
                if "message is not modified" in err:
                    return True
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ editCaption: {err}")
                return False
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Ошибка редактирования: {e}")
            return False

    # ------------------------------------------------------------------
    # Публичные методы
    # ------------------------------------------------------------------

    def send_photo_to_all_topics(self, photo_url, caption, parse_mode="HTML"):
        """Отправляет фото во все темы, сохраняет message_id."""
        self.active_message_ids.clear()
        for topic_id in TOPIC_IDS:
            msg_id = self._send_photo(photo_url, caption, parse_mode, message_thread_id=topic_id)
            if msg_id:
                self.active_message_ids[topic_id] = msg_id

    def send_message_to_all_topics(self, text, parse_mode="HTML"):
        """Отправляет текст во все темы."""
        for topic_id in TOPIC_IDS:
            self._send_message(text, parse_mode, message_thread_id=topic_id)

    def update_caption_in_all_topics(self, caption, parse_mode="HTML"):
        """
        Тихо редактирует подпись во всех активных сообщениях.
        Если message_id не сохранён — ничего не делает.
        """
        if not self.active_message_ids:
            return

        for topic_id, msg_id in self.active_message_ids.items():
            label = f"тема {topic_id}" if topic_id is not None else "General"
            ok = self._edit_caption(msg_id, caption, parse_mode)
            if ok:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 📝 Подпись обновлена ({label})")

    # ------------------------------------------------------------------
    # Форматирование
    # ------------------------------------------------------------------

    def format_manga_caption(self, manga_info, page_data=None, exp_gain_today=None, is_startup=False):
        """
        Подпись к фото манги.

        manga_info     — dict: title, slug, image, timestamp
        page_data      — dict: level, exp_current, exp_total, chance
        exp_gain_today — int или None
        is_startup     — True если стартовое сообщение
        """
        title = manga_info.get('title', '—')
        slug  = manga_info.get('slug', '')

        # Название копируемое + пустая строка после
        lines = [
            f"📚 <code>{title}</code>",
            "",
        ]

        if page_data:
            exp_cur = page_data.get('exp_current')
            exp_tot = page_data.get('exp_total')
            chance  = page_data.get('chance')

            if exp_cur is not None and exp_tot is not None:
                cur_fmt = f"{exp_cur:,}".replace(",", " ")
                tot_fmt = f"{exp_tot:,}".replace(",", " ")
                lines.append(f"⭐ Опыт: {cur_fmt} / {tot_fmt}")
            elif exp_cur is not None:
                lines.append(f"⭐ Опыт: {f'{exp_cur:,}'.replace(',', ' ')}")

            if chance is not None:
                lines.append(f"🎲 Шанс смены: {chance}%")

        lines.append("")
        # Ссылка скрыта под текстом
        lines.append(f'🔗 <a href="https://mangabuff.ru/alliances/10/boost">Перейти к вкладке альянса</a>')
        lines.append("")

        lines.append(f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")

        if exp_gain_today is not None:
            gain_fmt = f"{exp_gain_today:,}".replace(",", " ")
            lines.append(f"📈 Прирост за сегодня: +{gain_fmt} опыта")
        else:
            lines.append(f"📈 Прирост за сегодня: —")

        return "\n".join(lines)