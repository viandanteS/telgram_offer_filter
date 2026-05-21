import pytest
from main import split_multiple_offers

# --- I MESSAGGI FORNITI DA TE ---

MSG_PC = """Thermaltake Toughpower GF 3 1350W | PC ATX 3.0 Power Supply | PCIe Gen 5.0 | 80-Plus-Gold
 A soli: 181,36€  invece di: 257,90€
 APRI SU AMAZON https://www.amazon.it/dp/B0B7NV5M54/?tag=cavalieridelr-21&psc=1

 MSI MAG A850GL PCIE5, Alimentatore compatto da 850 W completamente modulare
 A soli: 114,48€  invece di: 122,24€
 APRI SU AMAZON https://www.amazon.it/dp/B0CB9MSJ5N/?tag=cavalieridelr-21&psc=1"""

MSG_FINISH = """PREZZO CONVENIENZA!

Finish Powergel, Gel Detersivo per Lavastoviglie Liquido, 42 Lavaggi, 940ml, Poteri Sgrassanti, Limone, Multiazione (Confezione da 4)

Passa da 31,96€ a soli 2,28€!



Venduto e spedito da Amazon  (senza costi con Prime e Prime Student) https://www.amazon.it/dp/B0F3JFRK13/?&tag=offertesulweb01-21&th=1&psc=1"""

MSG_PASTA = """La Molisana, Rigatoni n. 31, Pasta da Solo Grano Italiano
Passa da 121,49€ a soli 0,74€!La Molisana, Penne Rigate n. 20, Pasta da Solo Grano http://aaaa
Passa da 111,19€ a soli 0,74€!La Molisana, Linguine n. 6, Pasta da Solo Grano Italiano
http://aasssssss
Passa da 111,19€ a soli 0,74€!La Molisana, Spaghetti n. 15, Pasta da Solo Grano Italianohttp://aaaa
Passa da 1212,19€ a soli 0,74€!La Molisana, Spaghetto Quadrato n. 1, Pasta da Solo Grano http://aaaa
Passa da 1111,30€ a soli 0,74€!La Molisana, Trighetto n. 333, Pasta da Solo Grano Italiano http://aaaa
Passa da 199,19€ a soli 0,74€! http://aaaa"""

def test_split_pc_components():
    """Testa un messaggio formattato bene con doppi a capo tra le offerte"""
    risultato = split_multiple_offers(MSG_PC)
    
    assert len(risultato) == 2
    assert "Thermaltake" in risultato[0]
    assert "MSI MAG" in risultato[1]
    assert "http" in risultato[0] and "€" in risultato[0]

def test_split_finish_gel():
    """Testa un messaggio con TROPPI a capo. Deve restituire UN SOLO blocco valido."""
    risultato = split_multiple_offers(MSG_FINISH)
    
    # Lo splitter divide per \n\n, quindi creerà tanti piccoli frammenti. 
    # Ma SOLO l'ultimo frammento contiene sia '€' che 'http', quindi filtrerà gli altri.
    assert len(risultato) == 1
    assert "2,28€" in risultato[0]
    assert "http" in risultato[0]

def test_split_pasta_mangled():
    """Testa il messaggio rotto. Attenzione: questo evidenzia un limite della regex attuale!"""
    risultato = split_multiple_offers(MSG_PASTA)
    
    # Siccome in MSG_PASTA non c'è MAI un doppio a capo (\n\n) tra le offerte,
    # la nostra funzione attuale vede il tutto come UN UNICO BLOCCO GIGANTE.
    assert len(risultato) == 1
    assert "La Molisana" in risultato[0]