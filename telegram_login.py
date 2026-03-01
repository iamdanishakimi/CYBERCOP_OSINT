# save as: telegram_login.py
import asyncio
from telethon.sync import TelegramClient
from getpass import getpass

api_id = 32076729
api_hash = "9c6cebfae536b8c97e12cb90b0537187"
session_name = "cybercop_session"

async def login():
    client = TelegramClient(session_name, api_id, api_hash)
    await client.start()  # this will prompt for phone number + OTP
    print("Login successful! Session saved.")
    await client.disconnect()

asyncio.run(login())
