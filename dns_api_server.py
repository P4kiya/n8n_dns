#!/usr/bin/env python3
"""
Serveur HTTP simple pour l'API DNS
Alternative à n8n pour les tests ou déploiements simples
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import sys
from urllib.parse import urlparse, parse_qs

# Configuration
DNS_SCRIPT = "/opt/dns-automation/dns_manager.py"
PORT = 8080

class DNSAPIHandler(BaseHTTPRequestHandler):
    """Handler pour les requêtes API DNS"""
    
    def do_OPTIONS(self):
        """Gérer les requêtes CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        """Gérer les requêtes GET (liste des enregistrements)"""
        if self.path == '/dns-list' or self.path == '/api/dns/list':
            self.handle_list()
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        """Gérer les requêtes POST (ajout/suppression)"""
        if self.path == '/dns' or self.path == '/api/dns/add':
            self.handle_add()
        elif self.path == '/dns-remove' or self.path == '/api/dns/remove':
            self.handle_remove()
        else:
            self.send_error(404, "Not Found")
    
    def handle_list(self):
        """Lister les enregistrements DNS"""
        try:
            result = subprocess.run(
                ['python3', DNS_SCRIPT, 'list'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                response_data = json.loads(result.stdout)
                self.send_json_response(200, response_data)
            else:
                self.send_json_response(500, {
                    "success": False,
                    "error": result.stderr or "Unknown error"
                })
        except subprocess.TimeoutExpired:
            self.send_json_response(500, {
                "success": False,
                "error": "Command timeout"
            })
        except Exception as e:
            self.send_json_response(500, {
                "success": False,
                "error": str(e)
            })
    
    def handle_add(self):
        """Ajouter un enregistrement DNS"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Extraire les paramètres
            hostname = data.get('hostname')
            record_type = data.get('type')
            value = data.get('value')
            ttl = data.get('ttl', 3600)
            
            if not all([hostname, record_type, value]):
                self.send_json_response(400, {
                    "success": False,
                    "error": "Missing required parameters: hostname, type, value"
                })
                return
            
            # Exécuter le script
            result = subprocess.run(
                ['python3', DNS_SCRIPT, 'add', hostname, record_type, value, str(ttl)],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                response_data = json.loads(result.stdout)
                self.send_json_response(200, response_data)
            else:
                response_data = json.loads(result.stdout) if result.stdout else {
                    "success": False,
                    "error": result.stderr or "Unknown error"
                }
                self.send_json_response(500, response_data)
                
        except json.JSONDecodeError:
            self.send_json_response(400, {
                "success": False,
                "error": "Invalid JSON"
            })
        except subprocess.TimeoutExpired:
            self.send_json_response(500, {
                "success": False,
                "error": "Command timeout"
            })
        except Exception as e:
            self.send_json_response(500, {
                "success": False,
                "error": str(e)
            })
    
    def handle_remove(self):
        """Supprimer un enregistrement DNS"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Extraire les paramètres
            hostname = data.get('hostname')
            record_type = data.get('type')
            
            if not hostname:
                self.send_json_response(400, {
                    "success": False,
                    "error": "Missing required parameter: hostname"
                })
                return
            
            # Construire la commande
            cmd = ['python3', DNS_SCRIPT, 'remove', hostname]
            if record_type:
                cmd.append(record_type)
            
            # Exécuter le script
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                response_data = json.loads(result.stdout)
                self.send_json_response(200, response_data)
            else:
                response_data = json.loads(result.stdout) if result.stdout else {
                    "success": False,
                    "error": result.stderr or "Unknown error"
                }
                self.send_json_response(500, response_data)
                
        except json.JSONDecodeError:
            self.send_json_response(400, {
                "success": False,
                "error": "Invalid JSON"
            })
        except subprocess.TimeoutExpired:
            self.send_json_response(500, {
                "success": False,
                "error": "Command timeout"
            })
        except Exception as e:
            self.send_json_response(500, {
                "success": False,
                "error": str(e)
            })
    
    def send_json_response(self, status_code, data):
        """Envoyer une réponse JSON"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Override pour un logging personnalisé"""
        print(f"[{self.address_string()}] {format % args}")

def main():
    """Point d'entrée principal"""
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = PORT
    
    server_address = ('', port)
    httpd = HTTPServer(server_address, DNSAPIHandler)
    
    print(f"DNS API Server démarré sur le port {port}")
    print(f"Endpoints disponibles:")
    print(f"  POST /dns ou /api/dns/add - Ajouter un enregistrement")
    print(f"  POST /dns-remove ou /api/dns/remove - Supprimer un enregistrement")
    print(f"  GET /dns-list ou /api/dns/list - Lister les enregistrements")
    print(f"\nAppuyez sur Ctrl+C pour arrêter le serveur")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur...")
        httpd.server_close()

if __name__ == '__main__':
    main()

