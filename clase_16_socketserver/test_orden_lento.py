#!/usr/bin/env python3
"""Compara Bien vs Mal con clientes lentos.

Uso:
    python3 test_orden_lento.py bien
    python3 test_orden_lento.py mal
"""
import socketserver
import sys
import time

class Eco(socketserver.BaseRequestHandler):
    def handle(self):
        print(f'  atiendo a {self.client_address}')
        time.sleep(3)
        datos = self.request.recv(1024)
        self.request.sendall(datos.upper())

class Bien(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

class Mal(socketserver.TCPServer, socketserver.ThreadingMixIn):
    allow_reuse_address = True
    daemon_threads = True

modo = sys.argv[1] if len(sys.argv) > 1 else 'bien'
Servidor = Bien if modo == 'bien' else Mal
with Servidor(('localhost', 8080), Eco) as srv:
    print(f'Servidor: {Servidor.__name__}')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\nCortado')
