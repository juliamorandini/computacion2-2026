#!/usr/bin/env python3
import socketserver

class Handler(socketserver.StreamRequestHandler):
    def setup(self):
        print(f'  setup({self.client_address})')
        super().setup()

    def handle(self):
        print(f'  handle({self.client_address})')
        for linea in self.rfile:
            if linea.strip() == b'CRASH':
                raise RuntimeError('explotó')
            self.wfile.write(b'ok\n')

    def finish(self):
        print(f'  finish({self.client_address})')
        super().finish()

class Servidor(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def handle_error(self, request, client_address):
        import traceback
        print(f'  handle_error({client_address}): '
              f'{traceback.format_exc().strip().splitlines()[-1]}')

if __name__ == '__main__':
    with Servidor(('localhost', 8080), Handler) as srv:
        srv.serve_forever()
