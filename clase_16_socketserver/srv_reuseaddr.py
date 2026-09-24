#!/usr/bin/env python3
import socketserver

class Eco(socketserver.BaseRequestHandler):
    def handle(self):
        datos = self.request.recv(1024)
        self.request.sendall(datos.upper())

class Servidor(socketserver.TCPServer):
    allow_reuse_address = True

if __name__ == '__main__':
    with Servidor(('localhost', 8080), Eco) as srv:
        print('Escuchando...')
        srv.serve_forever()
