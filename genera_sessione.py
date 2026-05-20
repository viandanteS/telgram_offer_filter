import os
from dotenv import load_dotenv
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

print("Avvio generazione StringSession...")
with TelegramClient(StringSession(), API_ID, API_HASH) as client:
    print("\nEcco la tua StringSession. COPIALA E NON CONDIVIDERLA MAI CON NESSUNO:\n")
    print(client.session.save())