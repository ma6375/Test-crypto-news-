
import os
import json
import re
import html
import requests
from pathlib import Path

BOT_TOKEN = os.environ["BOT_TOKEN"]
BOT_CHAT_ID = os.environ["BOT_CHAT_ID"]
CHANNEL = os.environ["CHANNEL_USERNAME"].strip().lstrip("@")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

BOT_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
STATE_FILE = Path("last_post.json")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.5-flash:generateContent"
)


def send_message(text):
    # Telegram message limit is 4096 characters.
    if len(text) > 4000:
        text = text[:3950] + "\n\n[الخبر طويل؛ تم اختصار الرسالة]"
    r = requests.post(
        f"{BOT_URL}/sendMessage",
        data={"chat_id": BOT_CHAT_ID, "text": text},
        timeout=30,
    )
    r.raise_for_status()
    if not r.json().get("ok"):
        raise RuntimeError(r.text)


def rewrite_news(original_text):
    """Rewrite the news in simple Egyptian Arabic; preserve facts."""
    if not GEMINI_API_KEY or not original_text.strip():
        print("Gemini key missing or empty news; using original text.")
        return original_text

    prompt = f"""
أنت محرر أخبار متخصص في العملات الرقمية.
أعد صياغة الخبر التالي بالكامل بالعامية المصرية البسيطة والطبيعية.

قواعد إلزامية:
- حافظ على كل المعلومات والتفاصيل المهمة.
- لا تغيّر الأرقام أو الأسعار أو النسب أو التواريخ أو أسماء الأشخاص والشركات والعملات.
- لا تضف معلومات أو توقعات أو نصائح استثمارية من عندك.
- لا تحذف التحذيرات أو شروط الخبر أو سياقه.
- لا تترجم أسماء العملات والشركات المعروفة بطريقة تغيّر معناها.
- أخرج نص الخبر المعاد صياغته فقط، من غير مقدمة أو تعليق منك.

الخبر الأصلي:
{original_text}
"""

    try:
        response = requests.post(
            GEMINI_URL,
            params={"key": GEMINI_API_KEY},
            json={
                "contents": [
                    {"parts": [{"text": prompt}]}
                ],
                "generationConfig": {
                    "temperature": 0.2
                },
            },
            timeout=45,
        )
        response.raise_for_status()
        data = response.json()
        rewritten = data["candidates"][0]["content"]["parts"][0]["text"].strip()

        if rewritten:
            print("News rewritten successfully.")
            return rewritten

        print("Gemini returned empty text; using original.")
        return original_text

    except Exception as exc:
        print(f"Gemini rewrite failed; using original text. Error: {exc}")
        return original_text


def main():
    url = f"https://t.me/s/{CHANNEL}"
    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
    )
    response.raise_for_status()
    page_html = response.text

    posts = re.findall(
        r'<div class="tgme_widget_message_wrap[^"]*".*?'
        r'data-post="([^"]+)".*?'
        r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
        page_html,
        flags=re.S,
    )

    if not posts:
        print("No readable text posts found; channel may not expose web previews.")
        return

    latest = []
    for post_id, raw_text in posts:
        text = re.sub(r"<br\s*/?>", "\n", raw_text)
        text = re.sub(r"<[^>]+>", "", text)
        text = html.unescape(text).strip()
        if text:
            latest.append((post_id, text))

    if not latest:
        print("No non-empty text posts found.")
        return

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

    # First run: remember the latest post without forwarding old news.
    if not last_id:
        newest_id = max(
            int(post_id.split("/")[-1]) for post_id, _ in latest
        )
        STATE_FILE.write_text(json.dumps({"last_id": newest_id}))
        print("Initialized state; no old posts sent.")
        return

    for post_id, original_text in new_posts:
        link = f"https://t.me/{post_id}"
        rewritten_text = rewrite_news(original_text)
        message = f"{rewritten_text}\n\nالمصدر: {link}"
        send_message(message)

    if new_posts:
        newest_id = max(
            int(post_id.split("/")[-1]) for post_id, _ in new_posts
        )
        STATE_FILE.write_text(json.dumps({"last_id": newest_id}))
        print(f"Forwarded {len(new_posts)} new post(s).")
    else:
        print("No new posts.")


if __name__ == "__main__":
    main()
