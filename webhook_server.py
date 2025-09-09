from flask import Flask, request
import json
import os
import logging

app = Flask(__name__)
SUBSCRIBERS_FILE = "subscribers.json"

# יצירת הקובץ אם לא קיים
if not os.path.exists(SUBSCRIBERS_FILE):
    with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)

def load_subscribers():
    """טוען מנויים מהקובץ (רשימה ריקה אם הקובץ פגום)."""
    try:
        with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"שגיאה בקריאת subscribers.json: {e}")
        return []

def save_subscribers(subscribers):
    """שומר את רשימת המנויים לקובץ."""
    try:
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            json.dump(subscribers, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"שגיאה בשמירת subscribers.json: {e}")

@app.route("/", methods=["POST"])
def receive_update():
    data = request.get_json()
    try:
        if not data:
            return "No data", 400

        message = data.get("message")
        if not message:
            return "No message", 400

        chat_id = str(message["chat"]["id"])
        text = message.get("text", "").strip().lower()

        if text == "/start":
            subscribers = load_subscribers()
            if chat_id not in subscribers:
                subscribers.append(chat_id)
                save_subscribers(subscribers)
                print(f"✅ מנוי חדש נוסף: {chat_id}")
        elif text == "/stop":
            subscribers = load_subscribers()
            if chat_id in subscribers:
                subscribers.remove(chat_id)
                save_subscribers(subscribers)
                print(f"🛑 מנוי הוסר: {chat_id}")

        return "OK", 200

    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return "Error", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
