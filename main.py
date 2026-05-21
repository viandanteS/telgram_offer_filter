import os
import asyncio
import re
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityTextUrl # Serve per i link invisibili
import filters # Importiamo tutto il modulo per poter cambiare il flag SUPER_OFFERS_ACTIVE
from filters import evaluate_message
from keep_alive_server import start_web_server
from telethon.sessions import StringSession

load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
DESTINATION_GROUP = os.getenv("DESTINATION_GROUP", "me")

try:
    DESTINATION_GROUP = int(DESTINATION_GROUP)
except ValueError:
    pass 

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
message_queue = asyncio.Queue()

def split_multiple_offers(text: str) -> list[str]:
    """
    Divide un mega-messaggio e restituisce solo i blocchi che 
    assomigliano a vere offerte (es. contengono un link e un prezzo).
    """
    if not text:
        return []
    
    # --- IL FIX INTELLIGENTE ---
    # Se c'è al massimo 1 link, è palesemente una singola offerta.
    # Non la affettiamo, verifichiamo solo che sia valida e la restituiamo intera.
    if text.count("http") <= 1:
        if "http" in text and ("€" in text or "%" in text):
            return [text.strip()]
        return []

    # Se ci sono PIÙ link, allora è un mega-messaggio. 
    # Tentiamo la divisione per due o più a capo consecutivi (\n{2,})
    raw_chunks = re.split(r'\n{2,}|➿+', text)
    valid_chunks = []
    
    for chunk in raw_chunks:
        chunk_pulito = chunk.strip()
        if "http" in chunk_pulito and ("€" in chunk_pulito or "%" in chunk_pulito):
            valid_chunks.append(chunk_pulito)
            
    return valid_chunks

async def forward_to_remote(text: str, chat_name: str):
    print(f"[REMOTING] Invio al server remoto il messaggio da {chat_name}")

async def message_worker():
    while True:
        event, text = await message_queue.get()
        # BUG RISOLTO: Qui avevi scritto 'text = event.message.message'
        # che cancellava lo split e rimetteva il messaggio intero!
        
        if text:
            chat = await event.get_chat()
            chat_name = getattr(chat, 'title', getattr(chat, 'first_name', 'Chat Sconosciuta'))
            
            is_valid, reason = evaluate_message(text)
            
            if is_valid:
                print(f"✅ {reason} - Da: {chat_name}")
                alert_msg = f"🔔 **Trovato in {chat_name}**\n*Motivo: {reason}*\n\n{text}"
                await client.send_message(DESTINATION_GROUP, alert_msg)
                await forward_to_remote(text, chat_name)
            else:
                print(f"❌ Ignorato: {reason}")
        
        message_queue.task_done()
        
@client.on(events.NewMessage(incoming=True))
async def new_message_handler(event):
    testo_crudo = event.message.message
    if not testo_crudo:
        return

    # --- COMANDO SEGRETO: ATTIVAZIONE SUPER OFFERTE ---
    if testo_crudo.strip() == "activate n0w -superoffers":
        filters.SUPER_OFFERS_ACTIVE = not filters.SUPER_OFFERS_ACTIVE
        stato = "ATTIVATA 🔥" if filters.SUPER_OFFERS_ACTIVE else "DISATTIVATA ❄️"
        await event.reply(f"Modalità Super Offerte (>90%) {stato}!")
        return 

    # --- INIEZIONE DEI LINK NASCOSTI (Il Fix) ---
    if event.message.entities:
        # 1. Isoliamo solo le entità che sono Link Nascosti
        hidden_links = [ent for ent in event.message.entities if isinstance(ent, MessageEntityTextUrl)]
        
        # 2. Le ordiniamo AL CONTRARIO in base alla posizione (offset)
        hidden_links.sort(key=lambda x: x.offset, reverse=True)
        
        # 3. Inseriamo ogni URL nel testo crudo subito dopo la parola cliccata
        for ent in hidden_links:
            inserimento = ent.offset + ent.length
            # Tagliamo la stringa in due e ci infiliamo il link in mezzo
            testo_crudo = testo_crudo[:inserimento] + f" {ent.url}" + testo_crudo[inserimento:]

    # Ora il 'testo_crudo' ha tutti i link svelati e posizionati esattamente
    # nei loro rispettivi blocchi. Lo split funzionerà alla perfezione!
    singoli_messaggi = split_multiple_offers(testo_crudo)
    
    for msg_text in singoli_messaggi:
        await message_queue.put((event, msg_text))

async def main():
    start_web_server()
    for _ in range(2):
        asyncio.create_task(message_worker())
    
    await client.start()
    print("Userbot avviato con successo! In ascolto per nuovi messaggi...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())