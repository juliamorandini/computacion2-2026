#!/usr/bin/env python3
import socket
import struct

def enviar_mensaje(sock, payload: bytes):
    sock.sendall(struct.pack('!I', len(payload)) + payload)

def recibir_exacto(sock, n):
    datos = b''
    while len(datos) < n:
        pedazo = sock.recv(n - len(datos))
        if not pedazo:
            return None
        datos += pedazo
    return datos

def recibir_mensaje(sock):
    cab = recibir_exacto(sock, 4)
    if cab is None:
        return None
    (n,) = struct.unpack('!I', cab)
    return recibir_exacto(sock, n)

with socket.create_connection(('localhost', 8080)) as s:
    # Probar con \n adentro:
    enviar_mensaje(s, b'hay un \n adentro')
    enviar_mensaje(s, b'otro mensaje')
    enviar_mensaje(s, b'')                 # mensaje vacío
    enviar_mensaje(s, bytes(range(256)))   # binario arbitrario
    s.shutdown(socket.SHUT_WR)
    while True:
        r = recibir_mensaje(s)
        if r is None:
            break
        print(f'Recibido: {r!r}')
        