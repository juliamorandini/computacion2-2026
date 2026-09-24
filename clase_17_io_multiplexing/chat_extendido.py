#!/usr/bin/env python3
"""Chat con /nick, /lista, y framing correcto con buffer por cliente."""
import selectors
import socket
import sys

PUERTO = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

sel = selectors.DefaultSelector()
clientes = {}       # socket -> apodo
salida = {}         # socket -> bytes pendientes de enviar
buffers = {}        # socket -> buffer de lectura (framing por líneas)


def difundir(mensaje: bytes, excepto=None):
    for conn in clientes:
        if conn is excepto:
            continue
        salida[conn] = salida.get(conn, b'') + mensaje
        sel.modify(conn, selectors.EVENT_READ | selectors.EVENT_WRITE, manejar)


def aceptar(servidor, _m):
    conn, direccion = servidor.accept()
    conn.setblocking(False)
    apodo = f'{direccion[0]}:{direccion[1]}'
    clientes[conn] = apodo
    buffers[conn] = b''
    salida[conn] = b'Bienvenido. Comandos: /nick, /lista, /salir\n'
    sel.register(conn, selectors.EVENT_READ | selectors.EVENT_WRITE, manejar)
    print(f'+ {apodo}  ({len(clientes)} conectados)')
    difundir(f'* {apodo} se conectó\n'.encode(), excepto=conn)


def desconectar(conn):
    apodo = clientes.pop(conn, '?')
    salida.pop(conn, None)
    buffers.pop(conn, None)
    try:
        sel.unregister(conn)
    except KeyError:
        pass
    conn.close()
    print(f'- {apodo}  ({len(clientes)} conectados)')
    difundir(f'* {apodo} se fue\n'.encode())


def procesar_linea(conn, linea):
    """Devuelve False si el cliente pidió salir."""
    linea = linea.strip()
    if not linea:
        return True
    if linea == '/salir':
        return False
    if linea == '/lista':
        apodos = ', '.join(clientes.values())
        salida[conn] = salida.get(conn, b'') + f'Conectados: {apodos}\n'.encode()
        sel.modify(conn, selectors.EVENT_READ | selectors.EVENT_WRITE, manejar)
        return True
    if linea.startswith('/nick '):
        nuevo = linea[6:].strip()
        if nuevo:
            viejo = clientes[conn]
            clientes[conn] = nuevo
            difundir(f'* {viejo} ahora es {nuevo}\n'.encode())
        return True
    apodo = clientes.get(conn, '?')
    print(f'  <{apodo}> {linea}')
    difundir(f'<{apodo}> {linea}\n'.encode(), excepto=conn)
    return True


def manejar(conn, mascara):
    if mascara & selectors.EVENT_READ:
        try:
            datos = conn.recv(4096)
        except ConnectionResetError:
            desconectar(conn)
            return
        if not datos:
            desconectar(conn)
            return
        # Framing por líneas con buffer
        buffers[conn] += datos
        while b'\n' in buffers[conn]:
            linea, buffers[conn] = buffers[conn].split(b'\n', 1)
            try:
                texto = linea.decode('utf-8')
            except UnicodeDecodeError:
                texto = linea.decode('utf-8', errors='replace')
            if not procesar_linea(conn, texto):
                desconectar(conn)
                return

    if mascara & selectors.EVENT_WRITE:
        buf = salida.get(conn, b'')
        if buf:
            try:
                n = conn.send(buf)
            except (BrokenPipeError, ConnectionResetError):
                desconectar(conn)
                return
            salida[conn] = buf[n:]
        if not salida.get(conn) and conn in clientes:
            sel.modify(conn, selectors.EVENT_READ, manejar)


def main():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind(('0.0.0.0', PUERTO))
    servidor.listen(128)
    servidor.setblocking(False)
    sel.register(servidor, selectors.EVENT_READ, aceptar)

    print(f'Chat en 0.0.0.0:{PUERTO} ({type(sel).__name__})')
    try:
        while True:
            for clave, mascara in sel.select():
                clave.data(clave.fileobj, mascara)
    except KeyboardInterrupt:
        print('\nChat detenido')
    finally:
        sel.close()


if __name__ == '__main__':
    main()
