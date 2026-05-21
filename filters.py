import re
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List
from dotenv import load_dotenv

# --- CONFIGURAZIONI GLOBALI ---
load_dotenv()
KEYWORDS = os.getenv("KEYWORDS", "offerta,sconto,promo,amazon").split(",")
PREMIUM_BRANDS = os.getenv("PREMIUM_BRANDS", "columbia,the north face,stussy").split(",")
BLACKLIST = os.getenv("BLACKLIST", "terminato,esaurito").split(",")

# FLAG PER LA MODALITÀ SEGRETA
SUPER_OFFERS_ACTIVE = False 

@dataclass
class OfferContext:
    text: str
    text_lower: str
    discount_percent: int = 0
    is_premium_brand: bool = False
    brand_name: str = ""

# ==========================================
# 1. STRATEGIE DI ESTRAZIONE
# ==========================================
class ExtractorStrategy(ABC):
    @abstractmethod
    def extract(self, text: str) -> int:
        pass

class ExplicitPercentageExtractor(ExtractorStrategy):
    def extract(self, text: str) -> int:
        matches = re.findall(r'%?\s*(\d+)\s*%', text)
        return max([int(m) for m in matches]) if matches else 0

class MathPriceExtractor(ExtractorStrategy):
    def extract(self, text: str) -> int:
        matches = re.findall(r'(\d+(?:[\.,]\d{2})?)€', text)
        if len(matches) >= 2:
            prices = [float(p.replace(',', '.')) for p in matches]
            old_price, current_price = max(prices), min(prices)
            if old_price > 0 and current_price < old_price:
                return int(((old_price - current_price) / old_price) * 100)
        return 0

# ==========================================
# 2. NODI DELLA CATENA DI RESPONSABILITÀ (CoR)
# ==========================================
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
    """Fase 1: ORA È IL PRIMO NODO! Calcola lo sconto per tutti."""
    def __init__(self, strategies: List[ExtractorStrategy]):
        super().__init__()
        self.strategies = strategies

    def handle(self, context: OfferContext) -> tuple[bool, str]:
        for strategy in self.strategies:
            discount = strategy.extract(context.text)
            if discount > 0:
                context.discount_percent = discount
                break 
                
        if context.discount_percent == 0:
            return False, "Scartato: Nessuno sconto rilevato."
            
        return super().handle(context)

class KeywordHandler(Handler):
    """Fase 2: Controllo Keyword o Modalità Super Offerte."""
    def handle(self, context: OfferContext) -> tuple[bool, str]:
        # 1. Controllo Bypass (Super Offerte > 90%)
        if SUPER_OFFERS_ACTIVE and context.discount_percent >= 90:
            context.brand_name = "SUPER OFFERTA"
            return super().handle(context)

        # 2. Controllo Brand Premium
        for brand in PREMIUM_BRANDS:
            if brand.strip() in context.text_lower:
                context.is_premium_brand = True
                context.brand_name = brand.strip().title()
                return super().handle(context) 
                
        # 3. Controllo Keyword Generica
        if any(kw.strip() in context.text_lower for kw in KEYWORDS):
            return super().handle(context) 
            
        return False, "Scartato: Nessuna parola chiave rilevata."

class EvaluationHandler(Handler):
    """Fase 3: Valutazione matematica."""
    def handle(self, context: OfferContext) -> tuple[bool, str]:
        # Se è passato grazie al bypass, lo approviamo subito
        if context.brand_name == "SUPER OFFERTA":
            return super().handle(context)

        if context.is_premium_brand:
            if context.discount_percent >= 70:
                return super().handle(context)
            else:
                return False, f"Scartato: Brand {context.brand_name} richiede 70%, trovato {context.discount_percent}%"
        else:
            if context.discount_percent > 49:
                return super().handle(context)
            else:
                return False, f"Scartato: Sconto generico insufficiente ({context.discount_percent}%)"

class BlacklistHandler(Handler):
    """Fase 4: Controllo Blacklist finale."""
    def handle(self, context: OfferContext) -> tuple[bool, str]:
        if any(b.strip() in context.text_lower for b in BLACKLIST):
            return False, "Scartato in Blacklist (esaurito/terminato)"
            
        brand_str = f"[{context.brand_name}] " if context.brand_name else ""
        return True, f"Match Perfetto! {brand_str}Sconto: {context.discount_percent}%"

# ==========================================
# 3. ASSEMBLAGGIO ED ESECUZIONE
# ==========================================
def build_filter_pipeline() -> Handler:
    # ORDINE INVERTITO: Prima si estrae, poi si valuta la keyword!
    head = ExtractorHandler(strategies=[ExplicitPercentageExtractor(), MathPriceExtractor()])
    
    head.set_next(KeywordHandler()) \
        .set_next(EvaluationHandler()) \
        .set_next(BlacklistHandler())
        
    return head

PIPELINE = build_filter_pipeline()

def evaluate_message(text: str) -> tuple[bool, str]:
    context = OfferContext(text=text, text_lower=text.lower())
    return PIPELINE.handle(context)