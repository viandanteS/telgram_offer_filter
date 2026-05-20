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

# --- CONTESTO ---
@dataclass
class OfferContext:
    text: str
    text_lower: str
    discount_percent: int = 0
    is_premium_brand: bool = False
    brand_name: str = ""

# ==========================================
# 1. STRATEGIE DI ESTRAZIONE (Pattern Matching)
# ==========================================

class ExtractorStrategy(ABC):
    """Interfaccia base per gli estrattori di sconto."""
    @abstractmethod
    def extract(self, text: str) -> int:
        pass

class ExplicitPercentageExtractor(ExtractorStrategy):
    """Cerca esplicitamente il simbolo % (es. 'Sconto 50%')"""
    def extract(self, text: str) -> int:
        matches = re.findall(r'(\d+)\s*%', text)
        return max([int(m) for m in matches]) if matches else 0

class MathPriceExtractor(ExtractorStrategy):
    """Cerca due prezzi nel formato valuta e calcola la differenza."""
    def extract(self, text: str) -> int:
        matches = re.findall(r'(\d+(?:[\.,]\d{2})?)€', text)
        if len(matches) >= 2:
            prices = [float(p.replace(',', '.')) for p in matches]
            old_price, current_price = max(prices), min(prices)
            if old_price > 0 and current_price < old_price:
                return int(((old_price - current_price) / old_price) * 100)
        return 0

# Se domani ti serve un estrattore che legge i prezzi in dollari o con un pattern strano, 
# crei la classe qui e la aggiungi alla lista nel nodo ExtractorHandler.

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
        # Se siamo arrivati alla fine della catena senza essere scartati
        return True, "Approvato"

class KeywordHandler(Handler):
    """Fase 1: Controllo Keyword/Brand (Se non c'è interesse, scarta subito)"""
    def handle(self, context: OfferContext) -> tuple[bool, str]:
        # Controlla se è un brand premium
        for brand in PREMIUM_BRANDS:
            if brand.strip() in context.text_lower:
                context.is_premium_brand = True
                context.brand_name = brand.strip().title()
                return super().handle(context) # Trovato, passa al prossimo nodo
                
        # Controlla se c'è almeno una keyword generica
        if any(kw.strip() in context.text_lower for kw in KEYWORDS):
            return super().handle(context) # Trovato, passa al prossimo nodo
            
        return False, "Scartato: Nessuna parola chiave o brand rilevato."

class ExtractorHandler(Handler):
    """Fase 2: Prova le strategie di estrazione finché una non funziona."""
    def __init__(self, strategies: List[ExtractorStrategy]):
        super().__init__()
        self.strategies = strategies

    def handle(self, context: OfferContext) -> tuple[bool, str]:
        # Prova ogni strategia nell'ordine in cui sono state fornite
        for strategy in self.strategies:
            discount = strategy.extract(context.text)
            if discount > 0:
                context.discount_percent = discount
                break # Trovato! Interrompe il loop delle strategie
                
        if context.discount_percent == 0:
            return False, "Scartato: Impossibile estrarre lo sconto dal pattern."
            
        return super().handle(context)

class EvaluationHandler(Handler):
    """Fase 3: Valutazione dell'offerta in base ai criteri di business."""
    def handle(self, context: OfferContext) -> tuple[bool, str]:
        if context.is_premium_brand:
            if context.discount_percent >= 70:
                # Modifico il context text per il log o l'inoltro, opzionale
                return super().handle(context)
            else:
                return False, f"Scartato: Brand {context.brand_name} richiede 70%, trovato {context.discount_percent}%"
        else:
            if context.discount_percent > 49:
                return super().handle(context)
            else:
                return False, f"Scartato: Sconto generico insufficiente ({context.discount_percent}%)"

class BlacklistHandler(Handler):
    """Fase 4: Controllo Blacklist finale. Se passa questo, è True."""
    def handle(self, context: OfferContext) -> tuple[bool, str]:
        if any(b.strip() in context.text_lower for b in BLACKLIST):
            return False, "Scartato in Blacklist (esaurito/terminato)"
            
        # È l'ultimo nodo. Se non è in blacklist, l'offerta è valida al 100%.
        brand_str = f"[{context.brand_name}] " if context.is_premium_brand else ""
        return True, f"Match Perfetto! {brand_str}Sconto validato: {context.discount_percent}%"

# ==========================================
# 3. ASSEMBLAGGIO ED ESECUZIONE
# ==========================================

def build_filter_pipeline() -> Handler:
    """Costruisce la catena di responsabilità nel tuo esatto ordine."""
    
    # Inizializziamo il nodo estrattore con le strategie desiderate (in ordine di priorità)
    extractor_node = ExtractorHandler(strategies=[
        ExplicitPercentageExtractor(), 
        MathPriceExtractor()
    ])
    
    # Costruiamo il tubo
    head = KeywordHandler()
    head.set_next(extractor_node) \
        .set_next(EvaluationHandler()) \
        .set_next(BlacklistHandler())
        
    return head

# Istanziamo la pipeline una volta sola all'avvio dello script
PIPELINE = build_filter_pipeline()

def evaluate_message(text: str) -> tuple[bool, str]:
    """Funzione di ingresso da richiamare nel worker di Telethon."""
    context = OfferContext(text=text, text_lower=text.lower())
    return PIPELINE.handle(context)