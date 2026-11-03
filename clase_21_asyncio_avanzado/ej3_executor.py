#!/usr/bin/env python3
"""Clase 21 - Ejercicio 3 (obligatorio): sacar el trabajo del loop.

Este script cubre las partes B (con I/O-bound) y C. Las partes A y B
(CPU-bound) son executor.py de la clase; la parte D esta en
ej3_api_hashear.py + ej3_medir_api.py.

Uso:
    python3 executor.py                 # parte A
    python3 executor.py --paralelo      # parte B
    python3 ej3_executor.py             # B (sleep) y C
    python3 ej3_medir_api.py            # parte D

-----------------------------------------------------------------------
RESPUESTAS
-----------------------------------------------------------------------

Parte A: python3 executor.py  (calculo de ~5 s)
  1. Medido en esta maquina (detalle en RESULTADOS MEDIDOS al final):
         sin executor              1.48 s | peor atraso 1461.9 ms
         con ProcessPoolExecutor   1.73 s | peor atraso   57.8 ms
         con asyncio.to_thread     3.00 s | peor atraso   45.4 ms
  2. Sin executor el loop se atrasa casi todo lo que dura el calculo
     (1.46 s): el latido de 50 ms se despierta recien al terminar, o sea
     el loop estuvo congelado. Para un servidor significa que durante ese
     tiempo NINGUN otro pedido se atiende, ningun timeout se dispara, ni
     siquiera un healthcheck: para los demas clientes el servidor esta caido.
  3. El trabajo tarda lo mismo, pero lo que mejoro es la LATENCIA de todo
     lo demas: el loop sigue libre atendiendo pedidos. El executor no hace
     mas rapido el calculo, lo saca del hilo que atiende.
  4. El medidor mide el atraso de un asyncio.sleep porque dormir cede el
     control y el loop deberia despertarlo justo a tiempo: cualquier demora
     extra es tiempo en el que el loop no pudo ejecutar nada (estaba
     ocupado). Es un "latido" que delata el bloqueo.

Parte B: threads contra procesos
  5. Con 4 tareas CPU-bound: threads 8.86 s contra procesos 2.02 s (4.4x).
  6. Por el GIL (clase 10): los threads de un proceso se turnan para
     ejecutar bytecode, asi que 4 calculos puros se serializan. Los procesos
     tienen su propio interprete y su propio GIL: usan varios nucleos.
  7. Con UNA sola tarea no hay nadie con quien turnarse: un thread usa el
     GIL todo el tiempo y no se nota. El GIL solo pega cuando hay mas de un
     thread que quiere CPU a la vez.
  8. Con I/O-bound (time.sleep) siguen sin diferenciarse (ver seccion de
     abajo): sleep libera el GIL, entonces los threads tambien solapan las
     esperas. Y los threads son mas baratos de crear y no hay pickle.

Parte C: el costo de los procesos
  9. Una lambda da error: 'AttributeError: Can't pickle local object' o
     'PicklingError': el pool manda la funcion al otro proceso por pickle, y
     pickle serializa funciones POR NOMBRE (modulo + nombre). Una lambda
     no tiene nombre importable.
  10. Pasar una lista de un millon de numeros es mucho mas lento que pasar
      un numero: hay que serializar con pickle, copiar por un pipe y
      deserializar, tanto al ir como al volver (ver medicion abajo).
  11. Crear un ProcessPoolExecutor cuesta iniciar procesos nuevos (cientos de
      ms: arranca un interprete e importa modulos). Si se crea por tarea se
      paga eso cada vez; creado una vez (en el lifespan) se amortiza.

Parte D: en una API (python3 ej3_medir_api.py)
  12-15. Medicion 2 del TP2: ver RESULTADOS MEDIDOS.

RESULTADOS MEDIDOS (Windows, Python 3.13; el calculo dura distinto entre
corridas porque el CPU-bound compite con el medidor y con otros procesos)
  A. sin executor             1.48 s | peor atraso 1461.9 ms
     ProcessPoolExecutor      1.73 s | peor atraso   57.8 ms
     asyncio.to_thread        3.00 s | peor atraso   45.4 ms
  B. 4 tareas CPU-bound:  threads 8.86 s  contra  procesos 2.02 s  (4.4x)
     I/O-bound (sleep 1 s): threads 1.00 s, procesos 1.26 s (empatan; los
     procesos pagan arrancar)
     Una sola tarea CPU-bound: thread 0.37 s, proceso 0.39 s (empatan)
  C. lambda -> AttributeError: Can't get local object '...<lambda>'
     pasar 5: 0.37 ms | lista de 1.000.000: 74.96 ms (203x mas)
     crear ProcessPoolExecutor(4): 187.8 ms | ThreadPoolExecutor(4): 0.6 ms
  D. POST /hashear (3M vueltas, ~2 s en esta maquina):
       sin executor : GET /tareas tardo 1450.4 ms (esperó todo el calculo)
       con executor : GET /tareas tardo  226.3 ms
     Esos dos numeros son la medicion 2 del TP2.
"""
import asyncio
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor


def dormir(segundos):
    time.sleep(segundos)
    return segundos


def suma(lista):
    return sum(lista)


def doble(n):
    return n * 2


def calcular_ciclos(n):
    h = 0
    for i in range(n):
        h = (h * 31 + i) % 1_000_003
    return h


async def parte_b_io():
    print('=== Parte B.8: I/O-bound (time.sleep) con 4 tareas de 1 s ===')
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(4) as pool:
        t0 = time.perf_counter()
        await asyncio.gather(*(loop.run_in_executor(pool, dormir, 1) for _ in range(4)))
        print(f'  threads : {time.perf_counter() - t0:5.2f}s')
    with ProcessPoolExecutor(4) as pool:
        t0 = time.perf_counter()
        await asyncio.gather(*(loop.run_in_executor(pool, dormir, 1) for _ in range(4)))
        print(f'  procesos: {time.perf_counter() - t0:5.2f}s  (incluye arrancar los procesos)')


async def parte_b_una_tarea():
    print('\n=== Parte B.7: UNA sola tarea CPU-bound ===')
    loop = asyncio.get_running_loop()
    N = 8_000_000
    with ThreadPoolExecutor(1) as pool:
        t0 = time.perf_counter()
        await loop.run_in_executor(pool, calcular_ciclos, N)
        print(f'  thread : {time.perf_counter() - t0:5.2f}s')
    with ProcessPoolExecutor(1) as pool:
        await loop.run_in_executor(pool, doble, 1)       # calentar el proceso
        t0 = time.perf_counter()
        await loop.run_in_executor(pool, calcular_ciclos, N)
        print(f'  proceso: {time.perf_counter() - t0:5.2f}s  (empatan: no hay con quien turnarse)')


async def parte_c():
    print('\n=== Parte C.9: lambda en ProcessPoolExecutor ===')
    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor(1) as pool:
        try:
            await loop.run_in_executor(pool, lambda x: x + 1, 1)
        except Exception as e:
            print(f'  {type(e).__name__}: {e}')
    with ThreadPoolExecutor(1) as pool:
        r = await loop.run_in_executor(pool, lambda x: x + 1, 1)
        print(f'  con threads la lambda SI anda (no hay pickle): {r}')

    print('\n=== Parte C.10: costo de pasar datos ===')
    grande = list(range(1_000_000))
    with ProcessPoolExecutor(2) as pool:
        await loop.run_in_executor(pool, doble, 1)       # calentar
        await loop.run_in_executor(pool, doble, 1)
        t0 = time.perf_counter()
        await loop.run_in_executor(pool, doble, 5)
        chico = time.perf_counter() - t0
        t0 = time.perf_counter()
        await loop.run_in_executor(pool, suma, grande)
        gordo = time.perf_counter() - t0
    print(f'  pasar un numero            : {chico * 1000:8.2f} ms')
    print(f'  pasar lista de 1.000.000   : {gordo * 1000:8.2f} ms  ({gordo / chico:.0f}x)')

    print('\n=== Parte C.11: costo de crear el pool ===')
    t0 = time.perf_counter()
    with ProcessPoolExecutor(4) as pool:
        await loop.run_in_executor(pool, doble, 1)
    print(f'  crear + usar un ProcessPoolExecutor(4) una vez: '
          f'{(time.perf_counter() - t0) * 1000:7.1f} ms')
    t0 = time.perf_counter()
    with ThreadPoolExecutor(4) as pool:
        await loop.run_in_executor(pool, doble, 1)
    print(f'  crear + usar un ThreadPoolExecutor(4)        : '
          f'{(time.perf_counter() - t0) * 1000:7.1f} ms')


async def main():
    await parte_b_io()
    await parte_b_una_tarea()
    await parte_c()


if __name__ == '__main__':
    asyncio.run(main())
