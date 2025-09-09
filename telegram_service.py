import requests
import logging
import json
import os
from config import BOT_TOKEN

SUBSCRIBERS_FILE = "subscribers.json"

def load_subscribers():
    """טוען את רשימת המנויים מקובץ JSON. מחזיר רשימה ריקה אם הקובץ לא קיים/פגום."""
    if not os.path.exists(SUBSCRIBERS_FILE):
        logging.warning("⚠️ לא נמצא קובץ subscribers.json.")
        return []
    try:
        with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"שגיאה בקריאת קובץ מנויים: {e}")
        return []

def send_to_telegram(message: str):
    """שולח הודעה לכל המנויים בטלגרם עם עיצוב HTML."""
    print("🔥 מנסה לשלוח הודעה להפעלה...")

    subscribers = load_subscribers()
    if not subscribers:
        logging.warning("אין מנויים לשליחה.")
        return

    for chat_id in subscribers:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            response = requests.post(url, data=payload, timeout=5)

            if response.status_code == 200:
                print(f"✅ נשלחה הודעה ל־ {chat_id}")
            else:
                logging.error(f"❌ שגיאה בשליחה ל־{chat_id}: {response.status_code} - {response.text}")

        except requests.exceptions.RequestException as e:
            logging.error(f"❌ שגיאת רשת בשליחה ל־{chat_id}: {e}")
        except Exception as e:
            logging.error(f"❌ שגיאה לא צפויה בשליחה ל־{chat_id}: {e}")
