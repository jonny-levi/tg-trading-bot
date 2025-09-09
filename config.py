import os
from dotenv import load_dotenv
load_dotenv()

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
BOT_TOKEN       = os.getenv("BOT_TOKEN")
CHAT_ID         = os.getenv("CHAT_ID")
APP_URL         = os.getenv("APP_URL")

# אופציונלי ליוטיוב (ל-Watchlist)
YT_API_KEY       = os.getenv("YT_API_KEY")            # חובה אם רוצים משיכת סרטונים
YT_CHANNEL_IDS   = os.getenv("YT_CHANNEL_IDS", "")    # פסיק-מופרד: UCxxxx,UCyyyy
YOUTUBE_LOOKBACK = int(os.getenv("YOUTUBE_LOOKBACK", "10"))  # כמה סרטונים אחרונים לכל ערוץ
