#!/usr/bin/env python3
"""Servidor con trabajo CPU pesado: demuestra el problema del hilo único."""
import hashlib
import selectors
import socket

sel = selectors.DefaultSelector()

def aceptar(servidor):
    conn, direccion = servidor.accept()
    conn.setblocking(False)
    sel.register(conn, selectors.EVENT_READ, atender)
    print(f'+ cliente {direccion}')

def atender(conn):
    datos = conn.recv(4096)
    if not datos:
        sel.unregister(conn)
        conn.close()
        return
    # Trabajo pesado: ~2 segundos de CPU
    h = datos
    for _ in range(3_000_000):
        h = hashlib.sha256(h).digest()
    conn.sendall(h.hex().encode())

def main():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(('0.0.0.0', 8080))
    servidor.listen(128)
    servidor.setblocking(False)
    sel.register(servidor, selectors.EVENT_READ, aceptar)

    print(f'Pesado en 0.0.0.0:8080 ({type(sel).__name__})')
    try:
        while True:
            for clave, _m in sel.select():
                clave.data(clave.fileobj)
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
