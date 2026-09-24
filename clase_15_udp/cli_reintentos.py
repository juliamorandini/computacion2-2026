#!/usr/bin/env python3
"""Cliente UDP con reintentos."""
import socket
import sys


def pedir_con_reintentos(sock, mensaje, destino, intentos=5, timeout=0.5):
    """Manda y reintenta si no llega respuesta.

    Devuelve (respuesta, n_intentos) o (None, intentos) si no hubo suerte.
    """
    sock.settimeout(timeout)
    for i in range(1, intentos + 1):
        sock.sendto(mensaje, destino)
        try:
            respuesta, _ = sock.recvfrom(65535)
            return respuesta, i
        except TimeoutError:
            pass
    return None, intentos


if __name__ == '__main__':
    puerto = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    msg = sys.argv[2].encode() if len(sys.argv) > 2 else b'hola'

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        respuesta, intentos = pedir_con_reintentos(s, msg, ('localhost', puerto))
        if respuesta:
            print(f'Respuesta: {respuesta!r} (intentos: {intentos})')
        else:
            print(f'Sin respuesta después de {intentos} intentos')