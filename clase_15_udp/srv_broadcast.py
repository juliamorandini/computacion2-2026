#!/usr/bin/env python3
"""Servidor que responde al DISCOVER? con el nombre de la máquina."""
import socket
import sys

PUERTO = 8082

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', PUERTO))
    print(f'Escuchando broadcast en puerto {PUERTO}')
    while True:
        datos, origen = s.recvfrom(65535)
        print(f'  {origen}: {datos!r}')
        if datos == b'DISCOVER?':
            hostname = socket.gethostname().encode()
            s.sendto(b'SOY ' + hostname, origen)