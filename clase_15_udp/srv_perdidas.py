#!/usr/bin/env python3
"""Servidor eco UDP con pérdida simulada en la respuesta."""
import random
import socket
import sys

PROB_PERDIDA = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
PUERTO = 8080

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', PUERTO))
    print(f'Servidor UDP con {PROB_PERDIDA:.0%} pérdida en respuestas')
    while True:
        datos, origen = s.recvfrom(65535)
        if random.random() < PROB_PERDIDA:
            print(f'  [{origen[1]}] RECIBIDO {datos!r} — RESPUESTA DESCARTADA')
            continue
        print(f'  [{origen[1]}] RECIBIDO {datos!r} — respondiendo')
        s.sendto(datos, origen)