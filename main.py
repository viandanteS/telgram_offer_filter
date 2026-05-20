import os
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient, events

# 1. Carica le variabili d'ambiente
load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
KEYWORDS = [kw.strip().lower() for kw in os.getenv("KEYWORDS", "").split(",")]

# 2. Inizializza il client Telethon (Userbot)
# Il primo parametro 'session_locale' crea un file .session nella cartella
client = TelegramClient('session_locale', API_ID, API_HASH)

# 3. Crea la coda (Queue)
message_queue = asyncio.Queue()

async def forward_to_remote(text: str, chat_name: str):
    """
    Modulo fittizio per il futuro invio Socket/REST.
    """
    print(f"[REMOTING] Invio al server remoto il messaggio da {chat_name}")
    # await httpx.post(...) o client websocket

async def message_worker():
    """
    Questo è il "consumatore" della coda. Gira in background.
    Prende i messaggi accodati e li analizza uno ad uno.
    """
    while True:
        # Attende finché non c'è un messaggio nella coda
        event = await message_queue.get()
        text = event.message.message # Testo del messaggio
        
        if text:
            text_lower = text.lower()
            
            # Controllo keyword
            if any(kw in text_lower for kw in KEYWORDS):
                chat = await event.get_chat()
                chat_name = getattr(chat, 'title', 'Chat Privata')
                
                print(f"Keyword trovata! Inoltro messaggio da: {chat_name}")
                
                # Inoltra ai tuoi "Messaggi Salvati" ('me' è una keyword di Telethon)
                alert_msg = f"🔔 **Trovato in {chat_name}**:\n\n{text}"
                await client.send_message('me', text_lower)
                
                # Invoca il modulo remoto
                await forward_to_remote(text, chat_name)
        
        # Segnala alla coda che questo messaggio è stato elaborato
        message_queue.task_done()

# 4. Handler che ascolta i nuovi messaggi in arrivo
# Puoi specificare le chat da cui ascoltare inserendo chats=['@canale1', '@canale2']
@client.on(events.NewMessage(incoming=True))
async def new_message_handler(event):
    # Appena arriva un messaggio, non lo analizza qui, ma lo butta subito nella coda.
    # In questo modo Telegram non viene mai bloccato.
    await message_queue.put(event)

async def main():
    # Avvia il worker in background
    #for _ in range(2):
    asyncio.create_task(message_worker())
    
    # Avvia il client Telegram
    await client.start()
    print("Userbot avviato con successo! In ascolto per nuovi messaggi...")
    
    # Mantiene in vita lo script fino alla disconnessione
    await client.run_until_disconnected()

if __name__ == '__main__':
    # Esegue il loop di asyncio
    asyncio.run(main())