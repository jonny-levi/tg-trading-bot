# 📈 MoneyBot - Real-Time Microcap Stock Scanner Bot

MoneyBot is a real-time stock monitoring bot built in Python. It tracks microcap stocks (under $1B market cap) listed on the US exchange using the Finnhub API, analyzes sudden price movements, and sends Telegram alerts with trading recommendations and same-day news headlines.

---

## ⚡ Features

- 🔍 Scans microcap stocks in real time via WebSocket
- 📈 Detects sudden price changes and calculates percent change
- 📊 Calculates average price and analyzes momentum
- 🧠 Generates trading suggestions based on price behavior
- 📰 Fetches same-day news (max 3 headlines)
- 📤 Sends formatted alerts to a Telegram group or channel
- 💻 Designed for day traders who value speed and accuracy
- 🔐 API keys are stored securely using environment variables
- ☁️ Optimized to run on Railway cloud infrastructure

---

## 🛠 Tech Stack

- Python 3
- Finnhub API
- Telegram Bot API
- WebSocket (via `websocket-client`)
- Railway (Deployment)
- Multithreading + Logging

---

## 🚀 Installation

1. **Clone the repository:**

```bash
git clone https://github.com/your-username/MoneyBot.git
cd MoneyBot
Install dependencies:

bash
Copy
Edit
pip install -r requirements.txt
Set environment variables (in .env file or platform dashboard):

ini
Copy
Edit
FINNHUB_API_KEY=your_finnhub_key
BOT_TOKEN=your_telegram_bot_token
CHAT_ID=your_telegram_chat_id
APP_URL=https://your-subdomain.up.railway.app
Run the bot locally:

bash
Copy
Edit
python main.py
🧠 How It Works
The bot fetches a list of US microcap stocks.

For each stock, it checks market cap, opening price, and current price.

Subscribes via WebSocket to real-time price updates.

For each update:

Calculates percent change and moving average.

Sends alerts only once per symbol/percent range.

Includes real-time recommendation and up to 3 fresh news headlines.

📬 Example Alert Format
yaml
Copy
Edit
🚨 Hot Stock!
📈 SYMBOL
💰 Price: $4.95
📉 Open: $4.50
⚖️ Avg: $4.62
📊 Change: +10.00%
🧠 Recommendation: Positive momentum – consider entry
📰 News Today:
• 🔹 Company reports record Q2 earnings
• 🔹 Stock upgraded by major analyst
• 🔹 CEO announces strategic expansion
🔗 [Chart View on TradingView]
🤖 Deploying to Railway
Connect this repo to Railway

Set your environment variables in the project settings

Define Procfile:

makefile
Copy
Edit
worker: python main.py
Deploy and monitor logs via the Railway dashboard.

📄 License
This project is for educational and personal use. Always conduct your own due diligence before making investment decisions.

💬 Author
Developed by Roi Levi
📧 roilevi2212@gmail.com
