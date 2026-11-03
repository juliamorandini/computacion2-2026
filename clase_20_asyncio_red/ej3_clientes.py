#!/usr/bin/env python3
"""Clase 20 - Ejercicio 3 (obligatorio): concurrencia de clientes.

Descarga N cosas a la vez, acotando la concurrencia y manejando fallos.
Para que sea reproducible y no dependa de internet, las partes B, C y D
usan un servidor HTTP local (en un thread) que responde tras DEMORA s.

Uso:
    python3 ej3_clientes.py

Requiere: pip install httpx requests

-----------------------------------------------------------------------
RESPUESTAS
-----------------------------------------------------------------------

Parte A: python3 descargas.py  (12 descargas, suma de demoras 5.7 s)
  1. Tiempos medidos:
         secuencial            5.80 s
         gather (todas juntas) 0.87 s
         con semaforo de 4     1.57 s
         con timeout de 0.8 s  0.81 s  (1 cancelada)
     gather tarda lo que la mas lenta porque las 12 esperas (asyncio.sleep /
     I/O) estan en curso al mismo tiempo: el loop las intercala en un solo
     hilo y ninguna bloquea a las otras. En el secuencial cada await espera
     a la anterior, por eso suma.
  2. El semaforo deja correr 4 a la vez: son ~3 tandas, asi que tarda mas
     que gather (todas juntas) y mucho menos que secuencial.
  3. Con timeout de 0.8 s se cancelo 1 (la unica con demora > 0.8). A esa
     tarea asyncio.timeout le inyecto CancelledError en su await (se
     convierte en TimeoutError); se interrumpio la espera y se hizo la
     limpieza (finally). No se espera a que termine: se corta.

Parte B: HTTP real (aca contra el servidor local, ver medicion abajo)
  4. Medido (10 descargas de 0.3 s): secuencial 3.06 s contra concurrente
     0.32 s: mejora ~10x (pasa de la suma a lo que tarda una sola).
  5. El AsyncClient se crea una vez porque mantiene un pool de conexiones
     con keep-alive (clase 19): se reutiliza la conexion TCP y no se paga
     handshake (y TLS) en cada descarga. Uno por descarga = una conexion
     nueva cada vez y mas descriptores abiertos.
  6. Con requests (sincronico) dentro de la corrutina cada get() bloquea el
     event loop: las 10 corren una detras de otra y el tiempo vuelve a ser
     ~10 x DEMORA (medido: 3.04 s), igual que el secuencial. Es la regla de la clase 18/19:
     una llamada bloqueante dentro de una corrutina congela a todas.

Parte C: acotar
  7. Con Semaphore(3) y 10 descargas son 4 tandas: medido 1.22 s
     (~4 x 0.3 s), entre el secuencial (3.06 s) y el gather (0.32 s).
  8. Acotar evita: (a) agotar descriptores de archivo / puertos (cada
     conexion es un fd; 'Too many open files') y (b) saturar al servidor
     remoto o la red (te pueden bloquear con 429/ban o degradarle el
     servicio), ademas de usar memoria sin control.
  9. Sin semaforo y con 200 URLs a un servidor real, aparece
     'OSError: [Errno 24] Too many open files' cuando se supera el limite
     de fds (ulimit -n, 1024 en muchas distros Linux). En Windows no existe
     ese limite tan bajo: probado contra el servidor local, las 200 sin
     semaforo tardaron 1.8-2.5 s y en algunas corridas fallaron ~8 con
     ReadError (el servidor se satura); es el riesgo de no acotar.

Parte D: fallos
  10. Con gather normal, la primera excepcion se propaga al await: gather
      lanza esa excepcion y se pierde el resultado de TODAS, aunque las
      otras tareas siguen corriendo (no se cancelan) y terminan solas.
  11. Con return_exceptions=True gather espera a todas y devuelve una lista
      donde cada posicion es el resultado o el objeto excepcion. Se
      revisa despues con isinstance(r, Exception).
  12. Para el TP2 quiero return_exceptions=True: una tarea que falla no
      tiene que tirar abajo al lote entero ni hacer perder el resultado de
      las que anduvieron; cada fallo se registra en el estado de su tarea.
"""
import asyncio
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import requests

DEMORA = 0.3
PUERTO = 8765
BASE = f'http://127.0.0.1:{PUERTO}'


# ---------------------------------------------------------------
# Servidor local que tarda DEMORA segundos por pedido
# ---------------------------------------------------------------

class Lento(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'          # permite keep-alive

    def do_GET(self):
        time.sleep(DEMORA)
        cuerpo = b'x' * 1024
        self.send_response(200)
        self.send_header('Content-Length', str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, *a):
        pass


def levantar_servidor():
    srv = ThreadingHTTPServer(('127.0.0.1', PUERTO), Lento)
    srv.daemon_threads = True
    srv.request_queue_size = 512
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


# ---------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------

async def bajar(cliente, url):
    r = await cliente.get(url)
    return url, r.status_code, len(r.content)


async def bajar_con_requests(url):
    r = requests.get(url)                  # BLOQUEANTE dentro de una corrutina
    return url, r.status_code, len(r.content)


async def medir(etiqueta, corrutina):
    t0 = time.perf_counter()
    resultado = await corrutina
    print(f'  {etiqueta:<44} {time.perf_counter() - t0:6.2f}s')
    return resultado


async def parte_b():
    print(f'=== Parte B: 10 descargas de {DEMORA}s cada una ===')
    urls = [f'{BASE}/{i}' for i in range(10)]

    async with httpx.AsyncClient(timeout=10) as cliente:
        async def secuencial():
            return [await bajar(cliente, u) for u in urls]

        await medir('secuencial (httpx)', secuencial())
        await medir('concurrente: gather (httpx)',
                    asyncio.gather(*(bajar(cliente, u) for u in urls)))

    await medir('gather pero con requests (bloquea el loop)',
                asyncio.gather(*(bajar_con_requests(u) for u in urls)))


async def parte_c():
    print('\n=== Parte C: acotar la concurrencia ===')
    urls = [f'{BASE}/{i}' for i in range(10)]
    sem = asyncio.Semaphore(3)

    async def acotada(cliente, url):
        async with sem:
            return await bajar(cliente, url)

    async with httpx.AsyncClient(timeout=10) as cliente:
        await medir('10 URLs con Semaphore(3)  (4 tandas)',
                    asyncio.gather(*(acotada(cliente, u) for u in urls)))

    print('\n  200 URLs sin semaforo (limite de conexiones de httpx desactivado):')
    urls = [f'{BASE}/{i}' for i in range(200)]
    limites = httpx.Limits(max_connections=None, max_keepalive_connections=None)
    async with httpx.AsyncClient(timeout=30, limits=limites) as cliente:
        try:
            res = await medir('200 URLs sin semaforo',
                              asyncio.gather(*(bajar(cliente, u) for u in urls),
                                             return_exceptions=True))
            malas = [r for r in res if isinstance(r, Exception)]
            print(f'    fallaron {len(malas)} de 200'
                  + (f': {type(malas[0]).__name__}: {malas[0]}' if malas else ''))
        except OSError as e:
            print(f'    OSError: {e}')


async def parte_d():
    print('\n=== Parte D: una URL invalida entre las buenas ===')
    urls = [f'{BASE}/{i}' for i in range(4)] + ['http://127.0.0.1:1/cerrado']

    async with httpx.AsyncClient(timeout=5) as cliente:
        try:
            await asyncio.gather(*(bajar(cliente, u) for u in urls))
        except Exception as e:
            print(f'  gather normal: lanza {type(e).__name__} y NO devuelve '
                  f'ningun resultado')

        resultados = await asyncio.gather(*(bajar(cliente, u) for u in urls),
                                          return_exceptions=True)
    print('  return_exceptions=True: lista con resultados y excepciones:')
    for r in resultados:
        if isinstance(r, Exception):
            print(f'    ERROR  {type(r).__name__}')
        else:
            print(f'    ok     {r}')


async def main():
    await parte_b()
    await parte_c()
    await parte_d()


if __name__ == '__main__':
    levantar_servidor()
    asyncio.run(main())
