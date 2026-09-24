#!/usr/bin/env python3
"""Emisor de broadcast."""
import socket
import sys

enviar_setsockopt = '--sin-setsockopt' not in sys.argv

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
if enviar_setsockopt:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
s.settimeout(2.0)

try:
    s.sendto(b'DISCOVER?', ('255.255.255.255', 8082))
except OSError as e:
    print(f'Error al mandar: {e}')
    sys.exit(1)

try:
    datos, origen = s.recvfrom(4096)
    print(f'{origen} respondió: {datos!r}')
except TimeoutError:
    print('Nadie respondió')