import pytest
import filters

# 1. Iniettiamo ESATTAMENTE le tue configurazioni per isolare i test
filters.BLACKLIST = "terminato,terminata,esaurito".split(",")
filters.PREMIUM_BRANDS = "the north face,thenorthface,tnf,columbia".split(",")
filters.KEYWORDS = "tenda_per_campeggio,tenda,campeggio,camping,naturehike,salewa,ferrino,mammut,columbia,trekking,hiking,escursionismo,outdoor,materasso,materassino,stuoia,gonfiabile,autogonfiabile,brandina,bollitore,gavetta,fornello,jetboil,thermos,pentolino,tritatutto,mixer,macinino,bivacco,alpinismo,igloo,tarp,equipaggiamento,attrezzatura tecnica,zaino,sacco a pelo,montagna,natura".split(",")

from filters import evaluate_message

def test_outdoor_valido_sconto_standard():
    # Contiene "zaino" (keyword valida) e sconto del 50% (50€ -> 25€)
    testo = "Zaino da trekking super capiente! Lo paghi 25,00€ invece di 50,00€ http://link"
    is_valid, reason = evaluate_message(testo)
    
    assert is_valid is True
    assert "Match Perfetto" in reason

def test_outdoor_rifiutato_sconto_basso():
    # Contiene "gavetta" ma lo sconto è solo del 20% (100€ -> 80€)
    testo = "Gavetta in titanio in promo a 80,00€ invece di 100,00€ http://link"
    is_valid, reason = evaluate_message(testo)
    
    assert is_valid is False
    assert "insufficiente" in reason.lower()

def test_premium_brand_sconto_alto():
    # Contiene "the north face" e sconto > 80% (100€ -> 15€ = 85%)
    testo = "Giacca invernale The North Face a soli 15,00€ invece di 100,00€! http://link"
    is_valid, reason = evaluate_message(testo)
    
    assert is_valid is True
    assert "The North Face" in reason

def test_premium_brand_sconto_basso_rifiutato():
    # Contiene "columbia" ma sconto al 50% (che per la regola standard andrebbe bene, ma per i premium NO)
    testo = "Scarponi Columbia da montagna a 50,00€ invece di 100,00€ http://link"
    is_valid, reason = evaluate_message(testo)
    
    assert is_valid is False
    assert "richiede" in reason 

def test_blacklist_blocca_tutto():
    # Sconto eccellente (90%) su keyword valida ("ferrino"), ma è "esaurito"
    testo = "Tenda Ferrino a 10,00€ invece di 100,00€. Purtroppo esaurito. http://link"
    is_valid, reason = evaluate_message(testo)
    
    assert is_valid is False
    assert "Blacklist" in reason

def test_scartato_senza_keyword():
    # Sconto alto (60%) ma nessuna keyword in lista (parla di un televisore)
    testo = "Nuovo televisore 4K a 400€ invece di 1000€ http://link"
    is_valid, reason = evaluate_message(testo)
    
    assert is_valid is False
    assert "Nessuna parola chiave" in reason