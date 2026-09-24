#!/usr/bin/env python3
import os
import socketserver
import sys
import threading
import time

class Eco(socketserver.BaseRequestHandler):
    def handle(self):
        print(f'pid={os.getpid()} hilo={threading.current_thread().name}')
        time.sleep(3)
        datos = self.request.recv(1024)
        self.request.sendall(datos.upper())

# Descomentá UNA sola línea según lo que quieras probar:
class Servidor(socketserver.TCPServer):
# class Servidor(socketserver.ThreadingTCPServer):
# class Servidor(socketserver.ForkingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

if __name__ == '__main__':
    with Servidor(('localhost', 8080), Eco) as srv:
        print(f'Servidor: {Servidor.__name__}')
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print('\nCortado')
