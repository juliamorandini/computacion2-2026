#!/usr/bin/env python3
import multiprocessing
import socketserver

class Contador(socketserver.StreamRequestHandler):
    def handle(self):
        with self.server.lock:
            self.server.visitas.value += 1
            n = self.server.visitas.value
        self.wfile.write(f'visita {n}\n'.encode())

class Servidor(socketserver.ForkingTCPServer):
    allow_reuse_address = True
    max_children = 40

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.visitas = multiprocessing.Value('i', 0)
        self.lock = multiprocessing.Lock()

if __name__ == '__main__':
    with Servidor(('localhost', 8080), Contador) as srv:
        srv.serve_forever()
