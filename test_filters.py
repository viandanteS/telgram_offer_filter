import pytest
import filters

# 1. INIETTIAMO LE TUE VERE KEYWORD
filters.KEYWORDS = "tenda per campeggio,tenda,campeggio,camping,naturehike,salewa,ferrino,mammut,columbia,trekking,hiking,escursionismo,outdoor,materasso,materassino,stuoia,gonfiabile,autogonfiabile,brandina,bollitore,gavetta,fornello,jetboil,thermos,borraccia termica,pentolino,tritatutto,mixer,macinino,bivacco,frullatore,alpinismo,igloo,tarp,equipaggiamento,attrezzatura tecnica,zaino,sacco a pelo,montagna,natura".split(",")
filters.BLACKLIST = "terminato,terminata,esaurito".split(",")
filters.PREMIUM_BRANDS = "the north face,thenorthface,tnf,columbia,stussy,obey".split(",")

from filters import evaluate_message

# Estraiamo i singoli blocchi di testo per testarli come farebbe il worker
CHUNK_THERMALTAKE = """Thermaltake Toughpower GF 3 1350W | PC ATX 3.0 Power Supply
 A soli: 181,36€  invece di: 257,90€
 APRI SU AMAZON https://www.amazon.it/..."""

CHUNK_MSI = """MSI MAG A850GL PCIE5, Alimentatore compatto da 850 W
 A soli: 114,48€  invece di: 122,24€
 APRI SU AMAZON https://www.amazon.it/..."""

CHUNK_FINISH = """Passa da 31,96€ a soli 2,28€! Venduto da Amazon https://www.amazon.it/..."""

def test_ignora_offerte_fuori_nicchia():
    """L'alimentatore Thermaltake ha uno sconto del 29%. Ma non ha keyword outdoor."""
    filters.SUPER_OFFERS_ACTIVE = False
    
    is_valid, reason = evaluate_message(CHUNK_THERMALTAKE)
    
    assert is_valid is False
    assert "Nessuna parola chiave" in reason

def test_ignora_sconto_basso_fuori_nicchia():
    """L'alimentatore MSI ha uno sconto ridicolo (~6%). Nessuna keyword."""
    filters.SUPER_OFFERS_ACTIVE = False
    
    is_valid, reason = evaluate_message(CHUNK_MSI)
    
    assert is_valid is False
    assert "Nessuna parola chiave" in reason

def test_finish_gel_respinto_se_super_offerte_spento():
    """Il Finish è scontato del 92% (da 31,96€ a 2,28€), ma se la modalità Super è spenta e non ci sono keyword, deve fallire."""
    filters.SUPER_OFFERS_ACTIVE = False
    
    is_valid, reason = evaluate_message(CHUNK_FINISH)
    
    assert is_valid is False
    assert "Nessuna parola chiave" in reason

def test_finish_gel_approvato_se_super_offerte_acceso():
    """Test fondamentale: Modalità Super Offerte accesa. Il Finish ha il 92% di sconto. DEVE passare anche senza keyword."""
    filters.SUPER_OFFERS_ACTIVE = True 
    
    is_valid, reason = evaluate_message(CHUNK_FINISH)
    
    # Calcolo matematico atteso: ((31.96 - 2.28) / 31.96) * 100 = 92.8% -> Int(92)
    assert is_valid is True
    assert "SUPER OFFERTA" in reason
    assert "92%" in reason
    
    # Spegniamo il flag per non inquinare gli altri test
    filters.SUPER_OFFERS_ACTIVE = False

def test_controllo_keyword_outdoor_funzionante():
    """Un test di sicurezza per assicurarci che la tua nicchia funzioni ancora."""
    filters.SUPER_OFFERS_ACTIVE = False
    testo = "Zaino Naturehike in offerta da 100,00€ a 40,00€! https://link"
    
    is_valid, reason = evaluate_message(testo)
    
    assert is_valid is True
    assert "60%" in reason # Sconto del 60%


def test_tenda_campeggio_valida():
    """
    Test POSITIVO: Contiene la keyword esatta 'tenda per campeggio' 
    e ha uno sconto eccellente (60%).
    """
    filters.SUPER_OFFERS_ACTIVE = False
    
    testo = """Mega sconto outdoor! Tenda per campeggio Naturehike 2 posti.
    Passa da 150,00€ a soli 60,00€!
    Comprala qui: https://link..."""
    
    is_valid, reason = evaluate_message(testo)
    
    # Calcolo: ((150 - 60) / 150) * 100 = 60% 
    assert is_valid is True
    assert "Match Perfetto!" in reason
    assert "60%" in reason

def test_tenda_campeggio_rifiutata_sconto_basso():
    """
    Test NEGATIVO: Contiene la keyword, ma lo sconto è solo del 10%.
    Deve essere bloccato dall'EvaluationHandler.
    """
    filters.SUPER_OFFERS_ACTIVE = False
    
    testo = """Offerta imperdibile: Tenda per campeggio familiare 4 posti!
    A soli: 250,00€ invece di: 280,00€
    Link: https://link..."""
    
    is_valid, reason = evaluate_message(testo)
    
    # Calcolo: ((280 - 250) / 280) * 100 = 10% (inferiore alla soglia >49%)
    assert is_valid is False
    assert "Scartato: Sconto generico insufficiente" in reason
    assert "10%" in reason