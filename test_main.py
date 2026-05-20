import pytest
import asyncio
from unittest.mock import AsyncMock, patch
import main # Importiamo il modulo intero per sovrascrivere la coda
from main import message_worker, split_multiple_offers

# --- TEST UTILITY SPLIT MESSAGGI ---
def test_split_multiple_offers():
    # Aggiungiamo 'http' per passare il nuovo filtro intelligente!
    mega_messaggio = "Promo 1 a 10€ http://link\n\nPromo 2 a 20€ http://link\n\nPromo 3 a 30€ http://link"
    risultato = split_multiple_offers(mega_messaggio)
    
    assert len(risultato) == 3
    assert risultato[0] == "Promo 1 a 10€ http://link"

# --- TEST WORKER ASINCRONO ---
class MockChat:
    def __init__(self, title):
        self.title = title

class MockMessage:
    def __init__(self, text):
        self.message = text

class MockEvent:
    def __init__(self, text):
        self.message = MockMessage(text)
    async def get_chat(self):
        return MockChat("Canale Test")

@pytest.mark.asyncio
@patch('main.client') 
@patch('main.evaluate_message') 
@patch('main.forward_to_remote', new_callable=AsyncMock) 
async def test_worker_inoltra_se_valido(mock_remote, mock_evaluate, mock_client):
    # FIX LOOP: Creiamo una coda nuova di zecca solo per questo test
    main.message_queue = asyncio.Queue()

    mock_evaluate.return_value = (True, "Motivo di Test")
    mock_client.send_message = AsyncMock()

    finto_evento = MockEvent("Testo offerta")
    await main.message_queue.put(finto_evento)

    task = asyncio.create_task(message_worker())
    await main.message_queue.join()
    task.cancel()

    mock_evaluate.assert_called_once_with("Testo offerta")
    mock_client.send_message.assert_called_once()
    mock_remote.assert_called_once()

@pytest.mark.asyncio
@patch('main.client')
@patch('main.evaluate_message')
@patch('main.forward_to_remote', new_callable=AsyncMock)
async def test_worker_ignora_se_invalido(mock_remote, mock_evaluate, mock_client):
    # FIX LOOP: Creiamo un'altra coda nuova di zecca per questo test
    main.message_queue = asyncio.Queue()

    mock_evaluate.return_value = (False, "Sconto troppo basso")
    mock_client.send_message = AsyncMock()

    finto_evento = MockEvent("Offerta inutile")
    await main.message_queue.put(finto_evento)

    task = asyncio.create_task(message_worker())
    await main.message_queue.join()
    task.cancel()

    mock_evaluate.assert_called_once_with("Offerta inutile")
    mock_client.send_message.assert_not_called()
    mock_remote.assert_not_called()