#!/usr/bin/env python3
import socketserver
import sys
import threading
import time

class Handler(socketserver.StreamRequestHandler):

    def setup(self):
        super().setup()
        with self.server.lock:
            self.server.activos[self.client_address] = self.wfile
            self.server.nicks[self.client_address] = self.client_address[1]
            self.server.conexiones += 1

    def finish(self):
        with self.server.lock:
            self.server.activos.pop(self.client_address, None)
            self.server.nicks.pop(self.client_address, None)
        super().finish()

    def responder(self, texto):
        try:
            self.wfile.write((texto + '\n').encode())
        except (BrokenPipeError, ConnectionResetError):
            pass

    def broadcast(self, texto):
        with self.server.lock:
            destinatarios = list(self.server.activos.items())
        for direccion, wfile in destinatarios:
            try:
                wfile.write((texto + '\n').encode())
                wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

    def handle(self):
        self.responder('Servidor. AYUDA para comandos.')
        for linea in self.rfile:
            partes = linea.decode('utf-8', 'replace').strip().split(maxsplit=1)
            if not partes:
                continue
            cmd, resto = partes[0].upper(), (partes[1] if len(partes) > 1 else '')

            if cmd == 'TIME':
                self.responder(time.strftime('%Y-%m-%d %H:%M:%S'))
            elif cmd == 'ECHO':
                self.responder(resto)
            elif cmd == 'NICK':
                with self.server.lock:
                    self.server.nicks[self.client_address] = resto
                self.responder(f'Nick seteado a {resto}')
            elif cmd == 'QUIEN':
                with self.server.lock:
                    activos = sorted(
                        f'{nick}@{ip}:{p}'
                        for (ip, p), nick in self.server.nicks.items())
                self.responder(f'{len(activos)} conectados: ' + ', '.join(activos))
            elif cmd == 'BROADCAST':
                with self.server.lock:
                    nick = self.server.nicks[self.client_address]
                self.broadcast(f'[{nick}] {resto}')
            elif cmd == 'CONTADOR':
                with self.server.lock:
                    n = self.server.conexiones
                self.responder(f'Conexiones totales: {n}')
            elif cmd == 'AYUDA':
                self.responder('TIME | ECHO <texto> | NICK <nombre> | QUIEN | '
                               'BROADCAST <texto> | CONTADOR | QUIT')
            elif cmd == 'QUIT':
                self.responder('Chau')
                return
            else:
                self.responder(f'Comando desconocido: {cmd}')

    def handle_error(self, *args):
        print(f'Error atendiendo a {self.client_address}')

class Servidor(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conexiones = 0
        self.activos = {}
        self.nicks = {}
        self.lock = threading.Lock()

if __name__ == '__main__':
    puerto = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    with Servidor(('0.0.0.0', puerto), Handler) as srv:
        print(f'Escuchando en 0.0.0.0:{puerto}')
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print('\nCortado')