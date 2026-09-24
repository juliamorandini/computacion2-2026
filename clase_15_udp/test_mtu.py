#!/usr/bin/env python3
import socket
import sys

TAMANO = int(sys.argv[1]) if len(sys.argv) > 1 else 60000

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.settimeout(2.0)
    s.sendto(b'X' * TAMANO, ('localhost', 8080))
    try:
        respuesta, _ = s.recvfrom(65535)
        print(f'Recibidos: {len(respuesta)} bytes')
    except TimeoutError:
        print('Timeout: no llegó')