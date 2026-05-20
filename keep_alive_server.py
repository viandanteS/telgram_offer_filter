import threading
import http.server
import socketserver
import os


# --- SERVER WEB NATIVO (Zero Dipendenze) ---
class HealthCheckHandler(http.server.BaseHTTPRequestHandler):
    """Gestisce solo le richieste GET e risponde con un testo fisso."""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Il Bot Telegram e' online e vigile!")
    
    # Disabilitiamo i log per non inquinare il terminale a ogni ping
    def log_message(self, format, *args):
        pass

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        
def start_web_server():
    """Avvia il server in un thread separato."""
    port = int(os.environ.get('PORT', 8080))
    
    # Impedisce l'errore "Address already in use" ai riavvii
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("", port), HealthCheckHandler)
    
    # daemon=True fa sì che il thread muoia quando muore il bot principale
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    print(f"Server nativo avviato in background sulla porta {port}")