# MoneyBot — Telegram Trading Alert Bot

## Overview

MoneyBot is a Python Telegram bot for monitoring US microcap trading candidates. It uses Finnhub market data, optional YouTube-derived watchlists, WebSocket price streams, candle/metrics polling, and Telegram alerts to surface momentum events and same-day news.

> This project is an alerting and automation tool, not financial advice. Validate any strategy independently before trading.

## Features

- Scans US microcap candidates through Finnhub.
- Optional YouTube watchlist discovery from configured channel IDs.
- Real-time Finnhub WebSocket stream for selected symbols.
- Metrics polling for volume, VWAP, high-of-day, and related alert conditions.
- Telegram alert delivery for bot startup, candidate lists, market events, and errors.
- Same-day news integration and recommendation helpers.
- Flask keep-alive endpoint for hosted runtimes.
- Dockerfile, Fly.io config, GitHub Actions, and Kubernetes manifests included.

## Architecture / Structure

```text
main.py                    Main orchestration entrypoint
config.py                  Environment-backed configuration
stock_fetcher.py           Finnhub symbol/candidate and quote helpers
websocket_handler.py       Real-time Finnhub WebSocket event handling
metrics_service.py         Polling metrics and alert conditions
news_service.py            News lookup helpers
recommendation.py          Recommendation/summary logic
telegram_service.py        Telegram Bot API sender
youtube_watchlist.py       Optional YouTube watchlist extraction
keep_alive.py              Small Flask keep-alive web server
webhook_server.py          Flask webhook endpoint variant
Dockerfile                 Container image for hosted deployment
fly.toml                   Fly.io deployment config
Manifests/                 Kubernetes namespace/deployment/service manifests
.github/workflows/         Automation for deployment/run flows
```

## Prerequisites

- Python 3.10+ recommended.
- Finnhub API key.
- Telegram bot token and target chat/channel ID.
- Optional: YouTube Data API key and channel IDs.
- Optional deployment target: Docker, Fly.io, or Kubernetes.

## Getting Started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export FINNHUB_API_KEY="<finnhub-api-key>"
export BOT_TOKEN="<telegram-bot-token>"
export CHAT_ID="<telegram-chat-id>"
export APP_URL="http://localhost:8080"
python main.py
```

The bot starts a keep-alive web server, selects trading candidates, connects to real-time data streams, starts metrics polling, and sends status/alert messages to Telegram.

## Configuration

| Variable | Required | Description |
| --- | --- | --- |
| `FINNHUB_API_KEY` | Yes | Finnhub API key for symbols, quotes, metrics, news, and WebSocket. |
| `BOT_TOKEN` | Yes | Telegram bot token. |
| `CHAT_ID` | Yes for alerts | Telegram chat/channel ID for outgoing messages. |
| `APP_URL` | Recommended for hosted runtimes | Public URL used by hosting/keep-alive flows. |
| `YT_API_KEY` | Optional | YouTube Data API key for watchlist discovery. |
| `YT_CHANNEL_IDS` | Optional | Comma-separated YouTube channel IDs. |
| `YOUTUBE_LOOKBACK` | Optional | Number of recent videos to inspect per channel. Defaults to `10`. |

Use a local `.env` file for development if desired, but do not commit it.

## Deployment / Operations

### Docker

```bash
docker build -t tg-trading-bot:latest .
docker run --rm \
  -e FINNHUB_API_KEY="<finnhub-api-key>" \
  -e BOT_TOKEN="<telegram-bot-token>" \
  -e CHAT_ID="<telegram-chat-id>" \
  tg-trading-bot:latest
```

### Fly.io

The repository includes `fly.toml` and `.github/workflows/fly-deploy.yml`. Configure secrets in Fly/GitHub Actions rather than storing them in the repo.

### Kubernetes

Review and adjust `Manifests/` for namespace, image, and secret references, then apply:

```bash
kubectl apply -f Manifests/
kubectl logs -n <namespace> deploy/<deployment-name> -f
```

## Security Notes

- Keep all API keys and bot tokens in environment variables or platform secrets.
- Trading alerts can be wrong or delayed; do not rely on the bot as a sole decision-maker.
- Watch Finnhub and YouTube API rate limits.
- Avoid logging full tokens or sensitive Telegram chat details.
- Validate deployment manifests before exposing any webhook or keep-alive endpoint publicly.

## Author

Jonny Levi — [jonny-levi](https://github.com/jonny-levi)
