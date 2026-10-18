
import os
import asyncio
import requests
from telethon import TelegramClient, events

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]
BOT_CHAT_ID = os.environ["BOT_CHAT_ID"]
CHANNEL = os.environ["CHANNEL_USERNAME"].lstrip("@")

client = TelegramClient("crypto_session", API_ID, API_HASH)
BOT_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_text(text):
    response = requests.post(
        f"{BOT_URL}/sendMessage",
        data={"chat_id": BOT_CHAT_ID, "text": text},
        timeout=30,
    )
    response.raise_for_status()
    if not response.json().get("ok"):
        raise RuntimeError("Telegram send failed")

@client.on(events.NewMessage(chats=CHANNEL))
async def forward(event):
    text = event.message.message or ""
    link = f"https://t.me/{CHANNEL}/{event.message.id}"
    send_text(f"{text}\n\nSource: {link}" if text else link)

async def main():
    await client.start()
    print(f"Monitoring @{CHANNEL}")
    await client.run_until_disconnected()

asyncio.run(main())
