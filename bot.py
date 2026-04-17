import os
import json
import time
import threading
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PORT = int(os.getenv("PORT", "10000"))

if not BOT_TOKEN:
    raise ValueError("Не задано BOT_TOKEN")
if not CHANNEL_ID:
    raise ValueError("Не задано CHANNEL_ID")

API = f"https://api.telegram.org/bot{BOT_TOKEN}/"


def api_call(method, data=None):
    if data is None:
        data = {}
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(API + method, data=encoded)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def keyboard():
    return {
        "inline_keyboard": [
            [
                {"text": "🚨 Атака", "callback_data": "attack"},
                {"text": "🛡 Оборона", "callback_data": "defense"},
            ],
            [
                {"text": "📢 Збір", "callback_data": "gather"},
                {"text": "✅ Відбій", "callback_data": "clear"},
            ],
        ]
    }


def status_name(status):
    names = {
        "attack": "🚨 АТАКА",
        "defense": "🛡 ОБОРОНА",
        "gather": "📢 ЗБІР",
        "clear": "✅ ВІДБІЙ",
        "idle": "✅ СПОКІЙНО",
    }
    return names.get(status, status)


def pinned_text(status):
    return (
        "🔥 ЕКСТРЕНА ПІДМОГА КОМАНДИ\n\n"
        f"Статус: {status_name(status)}\n\n"
        "Натисни кнопку:\n"
        "🚨 Атака\n"
        "🛡 Оборона\n"
        "📢 Збір\n"
        "✅ Відбій"
    )


def alert_text(status):
    labels = {
        "attack": "🚨 АТАКА\nВсім терміново зайти в гру!",
        "defense": "🛡 ОБОРОНА\nВсім терміново зайти в гру на захист!",
        "gather": "📢 ЗБІР\nВсім зайти в гру та бути готовими!",
        "clear": "✅ ВІДБІЙ\nСитуацію завершено.",
    }
    current_time = time.strftime("%H:%M")
    return f"{labels.get(status, status_name(status))}\nЧас: {current_time}"


def send_message(chat_id, text_msg, reply_markup=None):
    data = {"chat_id": str(chat_id), "text": text_msg}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    return api_call("sendMessage", data)


def edit_message(chat_id, message_id, text_msg, reply_markup=None):
    data = {
        "chat_id": str(chat_id),
        "message_id": str(message_id),
        "text": text_msg,
    }
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    return api_call("editMessageText", data)


def pin_message(chat_id, message_id):
    return api_call(
        "pinChatMessage",
        {
            "chat_id": str(chat_id),
            "message_id": str(message_id),
            "disable_notification": "true",
        },
    )


def answer_callback(callback_query_id, text="Готово"):
    return api_call(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_query_id,
            "text": text,
        },
    )


def get_updates(offset=None):
    data = {"timeout": "25"}
    if offset is not None:
        data["offset"] = str(offset)
    return api_call("getUpdates", data)


def handle_post_command(user_chat_id):
    sent = send_message(CHANNEL_ID, pinned_text("idle"), keyboard())
    if not sent.get("ok"):
        send_message(user_chat_id, f"Помилка створення поста: {sent}")
        return

    message_id = sent["result"]["message_id"]
    pin_result = pin_message(CHANNEL_ID, message_id)

    if pin_result.get("ok"):
        send_message(user_chat_id, "Готово. Пост створений і закріплений.")
    else:
        send_message(user_chat_id, f"Пост створений, але не вдалося закріпити: {pin_result}")


def handle_callback(callback_query):
    callback_id = callback_query["id"]
    status = callback_query["data"]
    message = callback_query["message"]
    message_id = message["message_id"]
    chat_id = message["chat"]["id"]

    print("Натиснули кнопку:", status)

    edit_message(chat_id, message_id, pinned_text(status), keyboard())
    send_message(CHANNEL_ID, alert_text(status))
    answer_callback(callback_id, "Готово")


def bot_loop():
    print("Бот запущений...")
    offset = None

    while True:
        try:
            updates = get_updates(offset)
            if not updates.get("ok"):
                print("Помилка getUpdates:", updates)
                time.sleep(3)
                continue

            for update in updates.get("result", []):
                offset = update["update_id"] + 1

                if "message" in update:
                    message = update["message"]
                    text = message.get("text", "")
                    user_chat_id = message["chat"]["id"]

                    if text == "/post":
                        handle_post_command(user_chat_id)

                elif "callback_query" in update:
                    handle_callback(update["callback_query"])

        except Exception as e:
            print("Помилка:", e)
            time.sleep(3)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Bot is running".encode("utf-8"))

    def log_message(self, format, *args):
        return


def run_web_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    print(f"HTTP server running on port {PORT}")
    server.serve_forever()


if __name__ == "__main__":
    thread = threading.Thread(target=bot_loop, daemon=True)
    thread.start()
    run_web_server()
