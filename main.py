import datetime
import os
import asyncio
import re
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityTextUrl 
import filters 
from filters import evaluate_message
from keep_alive_server import start_web_server
from telethon.sessions import StringSession

load_dotenv()
API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION_STRING = os.getenv("SESSION_STRING")
DESTINATION_GROUP = os.getenv("DESTINATION_GROUP", "me")
ALLOWED_DOMAINS = ["amazon", "amzn", "amzlink", "zalando"]

try:
    DESTINATION_GROUP = int(DESTINATION_GROUP)
except ValueError:
    pass 

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
message_queue = asyncio.Queue()




async def forward_to_remote(text: str, chat_name: str):
    pass # Disattivato finché non implementi il server remoto

async def message_worker():
    while True:
        event, text = await message_queue.get()
        
        if text:
            chat = await event.get_chat()
            chat_name = getattr(chat, 'title', getattr(chat, 'first_name', 'Chat Sconosciuta'))
            
            # SPACCHETTAMENTO DEI 3 VALORI DA FILTERS.PY
            is_valid, reason, ctx = evaluate_message(text)
            
            if is_valid:
                prezzo_str = f"{ctx.current_price:.2f}€" if ctx.current_price > 0 else "N/D"
                # OUTPUT SUL TERMINALE
                print(f"✅ {reason} | Prezzo: {prezzo_str} | Link: {ctx.link} - Da: {chat_name}")
                
                # OUTPUT SU TELEGRAM (Formattato e ricco di dettagli)
                tipo_match = ctx.brand_name if ctx.brand_name else "Generica"
                alert_msg = (
                    f"🔔 **OFFERTA TROVATA IN: {chat_name}**\n"
                    f"🔥 **Tipo:** {tipo_match}\n"
                    f"📉 **Sconto:** {ctx.discount_percent}%\n"
                    f"📝 **Log:** {reason}\n"
                    + (f"➖" * 15) + "\n\n"
                    + f"{text}"
                )
                await client.send_message(DESTINATION_GROUP, alert_msg)
                await forward_to_remote(text, chat_name)
            else:
                ct = datetime.datetime.now().strftime("%m/%d %H:%M:%S")
                print(f"{ct} ❌ Ignorato: {reason}")
        
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
        msg = f"Modalità Super Offerte (>90%) {stato}!"
        await event.reply(msg)
        await client.send_message(DESTINATION_GROUP, msg)
        return 

    # --- INIEZIONE DEI LINK NASCOSTI (Solo domini autorizzati) ---
    if event.message.entities:
        hidden_links = []
        for ent in event.message.entities:
            if isinstance(ent, MessageEntityTextUrl):
                url_lower = ent.url.lower()
                has_valid_domain = any(domain in url_lower for domain in ALLOWED_DOMAINS)
                if has_valid_domain and "whatsapp" not in url_lower:
                    hidden_links.append(ent)
        
        hidden_links.sort(key=lambda x: x.offset, reverse=True)
        
        for ent in hidden_links:
            inserimento = ent.offset + ent.length
            testo_crudo = testo_crudo[:inserimento] + f" {ent.url} " + testo_crudo[inserimento:]

    # Affettiamo il messaggio se necessario
    singoli_messaggi = split_multiple_offers(testo_crudo)
    
    # --- IL FILTRO BUTTAFUORI GENERALE ---
    for msg_text in singoli_messaggi:
        # Controlliamo SE il pezzo contiene ALMENO uno dei domini autorizzati (sia in chiaro che srotolato)
        if any(domain in msg_text.lower() for domain in ALLOWED_DOMAINS):
            await message_queue.put((event, msg_text))
        else:
            # Questo fermerà Sunbet, Welcome to Favelas e qualsiasi altro store non in whitelist
            print(f"❌ Scartato a monte: Nessun link Amazon/Zalando valido trovato nel testo.")


def split_multiple_offers(text: str) -> list[str]:
    """
    Divide un mega-messaggio accumulando i pezzi finché 
    non formano un'offerta completa (Link + Prezzo).
    """
    if not text:
        return []
    
    # FIX: Se c'è al massimo 1 link, O AL MASSIMO 2 SIMBOLI €, è un'offerta singola!
    if text.count("http") <= 1 or text.count("€") <= 2:
        if "http" in text and ("€" in text or "%" in text):
            return [text.strip()]
        return []
    
    # Se ci sono più link, tagliamo per gli a capo...
    raw_chunks = re.split(r'\n{2,}|➿+|\n\s*[-—–_~]+\s*\n', text)
    valid_chunks = []
    buffer_chunk = ""
    
    # ...ma poi li RIUNIAMO in modo intelligente!
    for chunk in raw_chunks:
        buffer_chunk += chunk + "\n\n"
        
        # Appena il nostro 'cesto' contiene sia un link che un simbolo di prezzo/sconto, lo chiudiamo
        if "http" in buffer_chunk and ("€" in buffer_chunk or "%" in buffer_chunk):
            valid_chunks.append(buffer_chunk.strip())
            buffer_chunk = ""  # Svuota il cesto per l'eventuale offerta successiva
            
    # Rete di sicurezza vitale: se il coltello ha fatto danni e non ha trovato nulla,
    # ma il testo originale aveva tutto il necessario, non lo perdiamo!
    if not valid_chunks and "http" in text and ("€" in text or "%" in text):
        return [text.strip()]
        
    return valid_chunks




async def main():
    #start_web_server()
    for _ in range(2):
        asyncio.create_task(message_worker())
    
    await client.start()
    print("Userbot avviato con successo! In ascolto per nuovi messaggi...")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())