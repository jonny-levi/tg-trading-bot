# youtube_watchlist.py
import re
from typing import Iterable, Set, List
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from config import YT_API_KEY, YT_CHANNEL_IDS, YOUTUBE_LOOKBACK
import logging
import requests

TICKER_RE = re.compile(r"\b[A-Z]{2,5}\b")

def _get_us_symbols() -> Set[str]:
    # סט סמלים חוקיים כדי לסנן ראשי תיבות רגילים
    try:
        from config import FINNHUB_API_KEY
        url = f"https://finnhub.io/api/v1/stock/symbol?exchange=US&token={FINNHUB_API_KEY}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return {row.get("symbol","") for row in r.json() if row.get("symbol")}
    except Exception as e:
        logging.error("symbol universe fetch failed: %s", e)
        return set()

def _list_videos_for_channel(youtube, channel_id: str, max_results: int) -> List[str]:
    vids = []
    req = youtube.search().list(part="id", channelId=channel_id, maxResults=max_results, order="date", type="video")
    res = req.execute()
    for item in res.get("items", []):
        vid = item["id"].get("videoId")
        if vid: vids.append(vid)
    return vids

def _extract_tickers_from_video(video_id: str, valid: Set[str]) -> Set[str]:
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=("en", "he",))
    except Exception:
        return set()
    text = " ".join([seg.get("text","") for seg in transcript])
    cand = {m.group(0) for m in TICKER_RE.finditer(text)}
    return {c for c in cand if c in valid}

def fetch_watchlist_from_youtube() -> List[str]:
    """מחזיר רשימת טיקרים שהתגלו בערוצי יוטיוב שהוגדרו (אם יש API key וערוצים)."""
    if not YT_API_KEY or not YT_CHANNEL_IDS:
        return []
    try:
        youtube = build("youtube", "v3", developerKey=YT_API_KEY)
        valid = _get_us_symbols()
        out: Set[str] = set()
        for ch in [c.strip() for c in YT_CHANNEL_IDS.split(",") if c.strip()]:
            vids = _list_videos_for_channel(youtube, ch, max_results=YOUTUBE_LOOKBACK)
            for vid in vids:
                out |= _extract_tickers_from_video(vid, valid)
        return list(sorted(out))
    except Exception as e:
        logging.error("youtube watchlist failed: %s", e)
        return []
