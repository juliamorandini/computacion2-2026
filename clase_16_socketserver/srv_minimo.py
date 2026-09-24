#!/usr/bin/env python3
import socketserver

class Eco(socketserver.BaseRequestHandler):
    def handle(self):
        print(f'type(self.request) = {type(self.request)}')
        print(f'id(self) = {id(self)}')
        datos = self.request.recv(1024)
        self.request.sendall(datos.upper())

if __name__ == '__main__':
    socketserver.TCPServer(('localhost', 8080), Eco).serve_forever()