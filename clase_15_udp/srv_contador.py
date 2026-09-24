#!/usr/bin/env python3
"""Servidor que CUENTA cuántas veces hace el trabajo real."""
import random
import socket
import sys

PROB_PERDIDA = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
PUERTO = 8080

trabajos_ejecutados = 0

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', PUERTO))
    print(f'Servidor contador (pérdida respuestas: {PROB_PERDIDA:.0%})')
    try:
        while True:
            datos, origen = s.recvfrom(65535)
            trabajos_ejecutados += 1
            print(f'  TRABAJO #{trabajos_ejecutados}: {datos!r} de {origen}')
            if random.random() < PROB_PERDIDA:
                continue   # respuesta perdida
            s.sendto(datos.upper(), origen)
    except KeyboardInterrupt:
        print(f'\nTotal trabajos ejecutados: {trabajos_ejecutados}')