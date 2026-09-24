#!/usr/bin/env python3
"""Protocolo confiable mínimo sobre UDP — versión propia.

Cliente y servidor en el mismo proceso, con pérdida simulada.
"""
import random
import socket
import struct
import sys
import threading

PUERTO = 8098


def empaquetar(seq, payload):
    return struct.pack('!I', seq) + payload


def desempaquetar(datos):
    (seq,) = struct.unpack('!I', datos[:4])
    return seq, datos[4:]


def enviar_con_perdidas(sock, datos, destino, prob):
    if random.random() < prob:
        return
    sock.sendto(datos, destino)


def servidor(prob, listo, fin):
    vistos = {}            # seq -> respuesta ya calculada
    procesados = []        # cuántas veces se ejecutó el trabajo real

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('localhost', PUERTO))
        listo.set()
        s.settimeout(0.5)
        while not fin.is_set():
            try:
                datos, origen = s.recvfrom(65535)
            except TimeoutError:
                continue
            seq, payload = desempaquetar(datos)
            if seq in vistos:
                # Duplicado: reenviar SIN recalcular
                respuesta = vistos[seq]
            else:
                procesados.append(seq)
                respuesta = payload.upper()
                vistos[seq] = respuesta
            enviar_con_perdidas(s, empaquetar(seq, respuesta), origen, prob)

    servidor.procesados = procesados


def pedir(sock, seq, payload, destino, prob, intentos=10, timeout=0.3):
    sock.settimeout(timeout)
    for i in range(1, intentos + 1):
        enviar_con_perdidas(sock, empaquetar(seq, payload), destino, prob)
        try:
            datos, _ = sock.recvfrom(65535)
        except TimeoutError:
            continue
        seq_resp, respuesta = desempaquetar(datos)
        if seq_resp == seq:                # ignora respuestas viejas
            return respuesta, i
    return None, intentos


def main():
    prob = float(sys.argv[1]) if len(sys.argv) > 1 else 0.3
    mensajes = [b'hola', b'que', b'tal', b'todo', b'bien']

    listo, fin = threading.Event(), threading.Event()
    hilo = threading.Thread(target=servidor, args=(prob, listo, fin))
    hilo.start()
    listo.wait()

    print(f'Pérdida simulada: {prob:.0%}\n')
    total_intentos = 0
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        for seq, msg in enumerate(mensajes):
            respuesta, intentos = pedir(s, seq, msg, ('localhost', PUERTO), prob)
            total_intentos += intentos
            estado = respuesta.decode() if respuesta else 'SIN RESPUESTA'
            print(f'  seq={seq}  {msg.decode():<5} -> {estado:<5} ({intentos} intentos)')

    fin.set(); hilo.join()
    procesados = getattr(servidor, 'procesados', [])
    print(f'\nMensajes enviados por la app:      {len(mensajes)}')
    print(f'Envíos reales (con reintentos):    {total_intentos}')
    print(f'Veces que el servidor hizo trabajo: {len(procesados)}')


if __name__ == '__main__':
    main()