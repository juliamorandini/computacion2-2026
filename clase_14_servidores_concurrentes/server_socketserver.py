#!/usr/bin/env python3
"""Servidor eco con socketserver (threads)."""
import socketserver

class EchoHandler(socketserver.StreamRequestHandler):
    def handle(self):
        """Se llama una vez por conexión, en su propio thread."""
        for linea in self.rfile:                # framing por líneas, gratis
            self.wfile.write(linea)

class Servidor(socketserver.ThreadingTCPServer):
    allow_reuse_address = True                  # equivale a SO_REUSEADDR
    daemon_threads = True

if __name__ == '__main__':
    with Servidor(('0.0.0.0', 8080), EchoHandler) as srv:
        print(f'[socketserver] escuchando en 0.0.0.0:8080')
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print('\nServidor detenido')