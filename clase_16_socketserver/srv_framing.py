
#!/usr/bin/env python3
import socketserver

class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        for linea in self.rfile:
            self.wfile.write(b'recibi: ' + linea.strip() + b'\n')

class Servidor(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

if __name__ == '__main__':
    with Servidor(('localhost', 8080), Handler) as srv:
        srv.serve_forever()
