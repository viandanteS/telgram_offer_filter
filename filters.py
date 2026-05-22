import re
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv

load_dotenv()
KEYWORDS = os.getenv("KEYWORDS", "offerta,sconto,promo,amazon").split(",")
PREMIUM_BRANDS = os.getenv("PREMIUM_BRANDS", "columbia,the north face,stussy").split(",")
BLACKLIST = os.getenv("BLACK_LIST", "terminato,esaurito").split(",")


PREMIUM_BRANDS_PERCDISC=45
GENERAL_PERCDISC=50
SUPEROFFERS_PERCDISC=80
SUPER_OFFERS_ACTIVE = True 

@dataclass
class OfferContext:
    text: str
    text_lower: str
    discount_percent: int = 0
    is_premium_brand: bool = False
    brand_name: str = ""
    current_price: float = 0.0
    old_price: float = 0.0
    link: str = "N/D"

def parse_prices(text: str) -> list[float]:
    """
    Helper degli estrattori di sconto
    Cattura qualsiasi formato di prezzo vicino al simbolo € e lo converte in float
    senza mandare in crash il programma. Gestisce fino a 9.999,00 e oltre.
    """
    raw_matches = re.findall(r'([\d\.,]+)\s*€', text) + re.findall(r'€\s*([\d\.,]+)', text)
    prices = []
    
    for p in raw_matches:
        p_clean = p.strip('.,')
        if not p_clean:
            continue
            
        # Gestione dei vari formati possibili su Telegram
        if '.' in p_clean and ',' in p_clean:
            if p_clean.rfind(',') > p_clean.rfind('.'):
                # Formato IT: 1.110,00 -> 1110.00
                p_clean = p_clean.replace('.', '').replace(',', '.')
            else:
                # Formato EN: 1,110.00 -> 1110.00
                p_clean = p_clean.replace(',', '')
        elif ',' in p_clean:
            # Solo decimali: 8,00 -> 8.00
            p_clean = p_clean.replace(',', '.')
        else:
            # Se c'è solo un punto ed è seguito da 3 cifre (es. 1.110), è il separatore delle migliaia
            if re.search(r'\.\d{3}$', p_clean):
                p_clean = p_clean.replace('.', '')
                
        try:
            prices.append(float(p_clean))
        except ValueError:
            pass
            
    return prices


class ExtractorStrategy(ABC):
    @abstractmethod
    def extract(self, context: OfferContext) -> int:
        pass

class ExplicitPercentageExtractor(ExtractorStrategy):
    def extract(self, context: OfferContext) -> int:
        # Nascondiamo i link prima di cercare le percentuali
        text_without_links = re.sub(r'https?://[^\s]+', '', context.text)
        
        # FIX: Cerchiamo il % SOLO se è preceduto da parole come sconto, promo, coupon o dai segni meno
        matches = re.findall(r'(?:sconto|promo|coupon|-\s*|–\s*)\s*(\d+)\s*%', text_without_links, re.IGNORECASE)
        
        prices = parse_prices(context.text)
        if prices:
            context.current_price = min(prices)
            
        return max([int(m) for m in matches]) if matches else 0
    
class MathPriceExtractor(ExtractorStrategy):
    def extract(self, context: OfferContext) -> int:
        prices = parse_prices(context.text)
        
        if len(prices) >= 2:
            # La tua logica intatta: il prezzo massimo è il vecchio, il minimo è il nuovo
            old_price, current_price = max(prices), min(prices)
            
            if old_price > 0 and current_price < old_price:
                context.old_price = old_price
                context.current_price = current_price
                return int(((old_price - current_price) / old_price) * 100)
                
        return 0

class Handler(ABC):
    def __init__(self):
        self._next_handler = None
    def set_next(self, handler):
        self._next_handler = handler
        return handler 
    def handle(self, context: OfferContext) -> tuple[bool, str]:
        if self._next_handler:
            return self._next_handler.handle(context)
        return True, "Approvato"

class ExtractorHandler(Handler):
    def __init__(self, strategies: List[ExtractorStrategy]):
        super().__init__()
        self.strategies = strategies

    def handle(self, context: OfferContext) -> tuple[bool, str]:
        # Estrae il primo link visibile (dopo che il main.py li ha 'srotolati')
        link_match = re.search(r'(https?://[^\s]+)', context.text)
        if link_match:
            context.link = link_match.group(1)

        for strategy in self.strategies:
            discount = strategy.extract(context)
            if discount > 0:
                context.discount_percent = discount
                break 
                
        if context.discount_percent == 0:
            return False, "Scartato: Nessuno sconto rilevato."
            
        return super().handle(context)

class KeywordHandler(Handler):
    def handle(self, context: OfferContext) -> tuple[bool, str]:
        if SUPER_OFFERS_ACTIVE and context.discount_percent >= SUPEROFFERS_PERCDISC:
            context.brand_name = "SUPER OFFERTA"
            return super().handle(context)

        for brand in PREMIUM_BRANDS:
            if brand.strip() in context.text_lower:
                context.is_premium_brand = True
                context.brand_name = brand.strip().title()
                return super().handle(context) 
                
        if any(kw.strip() in context.text_lower for kw in KEYWORDS):
            return super().handle(context) 
            
        return False, "Scartato: Nessuna parola chiave rilevata."

class EvaluationHandler(Handler):
    def handle(self, context: OfferContext) -> tuple[bool, str]:
        if context.brand_name == "SUPER OFFERTA":
            return super().handle(context)

        if context.is_premium_brand:
            if context.discount_percent >= PREMIUM_BRANDS_PERCDISC:
                return super().handle(context)
            else:
                return False, f"Scartato: Brand {context.brand_name} richiede 70%, trovato {context.discount_percent}%"
        else:
            if context.discount_percent >= GENERAL_PERCDISC:
                return super().handle(context)
            else:
                return False, f"Scartato: Sconto generico insufficiente ({context.discount_percent}%)"

class BlacklistHandler(Handler):
    def handle(self, context: OfferContext) -> tuple[bool, str]:
        if any(b.strip() in context.text_lower for b in BLACKLIST):
            return False, "Scartato in Blacklist (esaurito/terminato)"
            
        brand_str = f"[{context.brand_name}] " if context.brand_name else ""
        return True, f"Match Perfetto! {brand_str}Sconto: {context.discount_percent}%"

def build_filter_pipeline() -> Handler:
    head = ExtractorHandler(strategies=[ExplicitPercentageExtractor(), MathPriceExtractor()])
    head.set_next(KeywordHandler()) \
        .set_next(EvaluationHandler()) \
        .set_next(BlacklistHandler())
    return head

PIPELINE = build_filter_pipeline()

def evaluate_message(text: str) -> tuple[bool, str, OfferContext]:
    context = OfferContext(text=text, text_lower=text.lower())
    is_valid, reason = PIPELINE.handle(context)
    return is_valid, reason, context