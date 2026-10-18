 
import os
import json
import re
import requests
from pathlib import Path

BOT_TOKEN = os.environ["BOT_TOKEN"]
BOT_CHAT_ID = os.environ["BOT_CHAT_ID"]
CHANNEL = os.environ["CHANNEL_USERNAME"].strip().lstrip("@")

BOT_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
STATE_FILE = Path("last_post.json")


def send_message(text):
    r = requests.post(
        f"{BOT_URL}/sendMessage",
        data={"chat_id": BOT_CHAT_ID, "text": text},
        timeout=30,
    )
    r.raise_for_status()
    if not r.json().get("ok"):
        raise RuntimeError(r.text)


def main():
    url = f"https://t.me/s/{CHANNEL}"
    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
    )
    response.raise_for_status()

    html = response.text
    posts = re.findall(
        r'<div class="tgme_widget_message_wrap[^"]*".*?'
        r'data-post="([^"]+)".*?'
        r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
        html,
        flags=re.S,
    )

    if not posts:
        print("No readable text posts found; channel may not expose web previews.")
        return

    latest = []
    for post_id, raw_text in posts:
        text = re.sub(r"<br\s*/?>", "\n", raw_text)
        text = re.sub(r"<[^>]+>", "", text)
        text = (
            text.replace("&amp;", "&")
                .replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("&quot;", '"')
        )
        latest.append((post_id, text.strip()))

    latest.sort(key=lambda item: int(item[0].split("/")[-1]))

    state = {}
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())

    last_id = int(state.get("last_id", 0))
    new_posts = [
        (post_id, text)
        for post_id, text in latest
        if int(post_id.split("/")[-1]) > last_id
    ]

    # أول تشغيل: سجّل أحدث منشور فقط لتجنب إرسال تاريخ القناة بالكامل.
    if not last_id:
        newest_id = max(
            int(post_id.split("/")[-1]) for post_id, _ in latest
        )
        STATE_FILE.write_text(json.dumps({"last_id": newest_id}))
        print("Initialized state; no old posts sent.")
        return

    for post_id, text in new_posts:
        link = f"https://t.me/{post_id}"
        send_message(f"{text}\n\nالمصدر: {link}")

    if new_posts:
        newest_id = max(
            int(post_id.split("/")[-1]) for post_id, _ in new_posts
        )
        STATE_FILE.write_text(json.dumps({"last_id": newest_id}))


if __name__ == "__main__":
    main()
    
