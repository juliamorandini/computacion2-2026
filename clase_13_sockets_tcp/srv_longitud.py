#!/usr/bin/env python3
"""Servidor con framing por prefijo de longitud (4 bytes, big-endian)."""
import socket
import struct

HOST, PUERTO = '0.0.0.0', 8080

def recibir_exacto(sock, n):
    """Lee EXACTAMENTE n bytes, o None si cerraron antes."""
    datos = b''
    while len(datos) < n:
        pedazo = sock.recv(n - len(datos))
        if not pedazo:
            return None
        datos += pedazo
    return datos

def recibir_mensaje(sock):
    """Devuelve el payload o None si el otro cerró."""
    cabecera = recibir_exacto(sock, 4)
    if cabecera is None:
        return None
    (longitud,) = struct.unpack('!I', cabecera)
    if longitud == 0:
        return b''
    return recibir_exacto(sock, longitud)

def enviar_mensaje(sock, payload: bytes):
    sock.sendall(struct.pack('!I', len(payload)) + payload)

def atender(conn, direccion):
    print(f'Conexión desde {direccion}')
    try:
        while True:
            msg = recibir_mensaje(conn)
            if msg is None:
                print(f'{direccion} cerró')
                break
            print(f'mensaje: {msg!r}')
            enviar_mensaje(conn, msg.upper())
    except (ConnectionResetError, BrokenPipeError) as e:
        print(f'{direccion} se desconectó: {e}')

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PUERTO))
        srv.listen(5)
        print(f'Escuchando en {HOST}:{PUERTO}...')
        while True:
            conn, dir = srv.accept()
            with conn:
                atender(conn, dir)

if __name__ == '__main__':
    main()
    