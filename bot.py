# ГОТОВИЙ БОТ ДЛЯ 24/7 (Render / сервер)
import json
import time
import urllib.parse
import urllib.request
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID"))

API = f"https://api.telegram.org/bot{BOT_TOKEN}/"


def api_call(method, data=None):
    if data is None:
        data = {}
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(API + method, data=encoded)
    with urllib.request.urlopen(req) as response:
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


def text(status):
    names = {
        "attack": "🚨 АТАКА",
        "defense": "🛡 ОБОРОНА",
        "gather": "📢 ЗБІР",
        "clear": "✅ ВІДБІЙ",
        "idle": "✅ СПОКІЙНО"
    }

    return f"""🔥 ЕКСТРЕНА ПІДМОГА КОМАНДИ

Статус: {names.get(status)}

Натисни кнопку:
🚨 Атака
🛡 Оборона
📢 Збір
✅ Відбій
"""


def send_message(text_msg, reply_markup=None):
    data = {"chat_id": CHANNEL_ID, "text": text_msg}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    return api_call("sendMessage", data)


def edit_message(message_id, text_msg):
    data = {
        "chat_id": CHANNEL_ID,
        "message_id": message_id,
        "text": text_msg,
        "reply_markup": json.dumps(keyboard())
    }
    return api_call("editMessageText", data)


def pin(message_id):
    return api_call("pinChatMessage", {
        "chat_id": CHANNEL_ID,
        "message_id": message_id
    })


def get_updates(offset=None):
    data = {"timeout": 30}
    if offset:
        data["offset"] = offset
    return api_call("getUpdates", data)


def answer_callback(callback_id):
    return api_call("answerCallbackQuery", {
        "callback_query_id": callback_id
    })


def main():
    print("Бот запущений...")
    offset = None

    while True:
        try:
            updates = get_updates(offset)

            for update in updates.get("result", []):
                offset = update["update_id"] + 1

                if "message" in update:
                    if update["message"].get("text") == "/post":
                        msg = send_message(text("idle"), keyboard())
                        message_id = msg["result"]["message_id"]
                        pin(message_id)

                if "callback_query" in update:
                    callback = update["callback_query"]
                    status = callback["data"]

                    names = {
                        "attack": "🚨 АТАКА",
                        "defense": "🛡 ОБОРОНА",
                        "gather": "📢 ЗБІР",
                        "clear": "✅ ВІДБІЙ"
                    }

                    edit_message(callback["message"]["message_id"], text(status))
                    send_message(f"{names.get(status)}\nВсім зайти в гру!")

                    answer_callback(callback["id"])

        except Exception as e:
            print("Помилка:", e)
            time.sleep(2)


if __name__ == "__main__":
    main()
