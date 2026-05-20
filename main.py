import os
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient, events
#messaggi multipli in unica stringa (bisogna dividerli in più messaggi e riportarli in coda)
# Importiamo il nostro nuovo modulo di filtraggio!
from filters import evaluate_message

load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

# Prende l'ID del gruppo di destinazione. Se non c'è, usa 'me' di default
DESTINATION_GROUP = os.getenv("DESTINATION_GROUP", "me")

# Se DESTINATION_GROUP è un numero (ID), va convertito in intero
try:
    DESTINATION_GROUP = int(DESTINATION_GROUP)
except ValueError:
    pass # Lascialo come stringa (es. 'me' o '@username')

client = TelegramClient('session_locale', API_ID, API_HASH)
message_queue = asyncio.Queue()

def split_multiple_offers(text: str) -> list[str]:
    """
    Divide un mega-messaggio e restituisce solo i blocchi che 
    assomigliano a vere offerte (es. contengono un link e un prezzo).
    """
    if not text:
        return []
    
    # Dividiamo per doppio a capo
    raw_chunks = text.split('\n\n')
    valid_chunks = []
    
    for chunk in raw_chunks:
        chunk_pulito = chunk.strip()
        
        # Un frammento per essere un'offerta DEVE avere almeno un link (http) 
        # e un simbolo dell'euro (€) o di percentuale (%).
        if "http" in chunk_pulito and ("€" in chunk_pulito or "%" in chunk_pulito):
            valid_chunks.append(chunk_pulito)
            
    return valid_chunks

async def forward_to_remote(text: str, chat_name: str):
    print(f"[REMOTING] Invio al server remoto il messaggio da {chat_name}")
    # await httpx.post(...)

async def message_worker():
    while True:
        event = await message_queue.get()
        text = event.message.message
        
        if text:
            # 1. Recupero accurato del nome della chat
            chat = await event.get_chat()
            # Prova a prendere il titolo (gruppi/canali), altrimenti il nome (utenti privati)
            chat_name = getattr(chat, 'title', getattr(chat, 'first_name', 'Chat Sconosciuta'))
            
            # 2. Deleghiamo l'analisi al nostro motore di Regole
            is_valid, reason = evaluate_message(text)
            
            if is_valid:
                print(f"✅ {reason} - Da: {chat_name}")
                
                alert_msg = f"🔔 **Trovato in {chat_name}**\n*Motivo: {reason}*\n\n{text}"
                
                # Inoltra al gruppo specifico indicato nel .env
                await client.send_message(DESTINATION_GROUP, alert_msg + text)
                
                # Invoca il modulo remoto
                await forward_to_remote(text, chat_name)
            else:
                # Puoi scommentare questa riga per debuggare i messaggi ignorati
                print(f"❌ Ignorato: {reason}")
                #pass
        
        message_queue.task_done()


@client.on(events.NewMessage(incoming=True))
async def new_message_handler(event):
    text = event.message.message
    if text:
        # Usa la funzione di split
        singoli_messaggi = split_multiple_offers(text)
        for msg_text in singoli_messaggi:
            # Creiamo un "falso" evento o accodiamo direttamente una tupla (chat, testo)
            # Per semplicità, possiamo mettere nella coda solo i dati che ci servono:
            await message_queue.put((event, msg_text))

async def main():
    # Avviamo 2 worker paralleli per smaltire più velocemente le allerte!
    for _ in range(3):
        asyncio.create_task(message_worker())
    
    await client.start()
    print("Userbot avviato con successo! In ascolto per nuovi messaggi...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())