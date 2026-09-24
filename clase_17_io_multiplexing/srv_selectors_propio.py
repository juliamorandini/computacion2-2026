#!/usr/bin/env python3
"""Servidor eco reescrito con selectors."""
import selectors
import socket

sel = selectors.DefaultSelector()

def aceptar(servidor):
    conn, direccion = servidor.accept()
    conn.setblocking(False)
    sel.register(conn, selectors.EVENT_READ, atender)
    print(f'+ cliente {direccion}')

def atender(conn):
    try:
        datos = conn.recv(4096)
    except ConnectionResetError:
        cerrar(conn)
        return
    if datos:
        conn.sendall(datos)
    else:
        cerrar(conn)

def cerrar(conn):
    sel.unregister(conn)     # ANTES de close
    conn.close()
    print('- cliente')

def main():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(('0.0.0.0', 8080))
    servidor.listen(128)
    servidor.setblocking(False)
    sel.register(servidor, selectors.EVENT_READ, aceptar)

    print(f'Implementación: {type(sel).__name__}')
    try:
        while True:
            for clave, _m in sel.select():
                clave.data(clave.fileobj)
    except KeyboardInterrupt:
        pass
    finally:
        sel.close()

if __name__ == '__main__':
    main()
