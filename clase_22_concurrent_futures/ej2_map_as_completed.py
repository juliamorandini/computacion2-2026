#!/usr/bin/env python3
"""Clase 22 - Ejercicio 2 (obligatorio): map contra as_completed.

Uso:
    python3 ej2_map_as_completed.py

-----------------------------------------------------------------------
RESPUESTAS
-----------------------------------------------------------------------

Parte A: python3 patrones.py  (trabajos: lenta 0.5, rapida 0.1, media 0.2, otra 0.4)
  1. Tiempos medidos (aprox., se repiten en la salida de este script):
       map():          lenta 0.50 | rapida 0.50 | media 0.50 | otra 0.50
       as_completed(): rapida 0.10 | media 0.20 | otra 0.40 | lenta 0.50
  2. Con map, el resultado de 'rapida' estuvo CALCULADO a los 0.10 s pero
     recien estuvo DISPONIBLE (el for lo recibio) a los 0.50 s, porque map
     entrega en el orden de entrada y 'lenta' va primera: el for se queda
     esperando a 'lenta' y recien despues recibe las demas de golpe.
  3. El total es el mismo porque las cuatro tareas se ejecutan en paralelo
     en los dos casos (4 workers para 4 tareas): el total es lo que tarda la
     mas lenta (0.5 s). Lo unico que cambia es el orden/momento de entrega.
  4. map garantiza que los resultados salen en el MISMO ORDEN que las
     entradas; as_completed no (sale primero lo que termina primero).

Parte B: cual elegir
  5. 1000 URLs -> lista de codigos en el mismo orden: MAP. Necesito el orden
     de entrada y no me importa cuando llega cada uno.
  6. Barra de progreso con 1000 archivos: AS_COMPLETED. Cada resultado
     que termina avanza la barra apenas llega; con map la barra se trabaria
     detras del primer archivo lento.
  7. 50 imagenes guardadas apenas lleguen: AS_COMPLETED. Se escribe cada
     una en disco apenas esta lista, sin esperar a las anteriores.
  8. Promedio de f(x) sobre 100 numeros: MAP. El orden no importa para el
     promedio pero map es mas simple (sum(pool.map(f, nums)) / n) y hay que
     esperar a todas igual para calcularlo.

Parte C: la correspondencia
  9. as_completed no mantiene el orden, asi que hay que guardar un dict
     {future: dato_de_entrada} y buscar con ese future.
  10. Implementado abajo en patron_diccionario() (5 URLs, reporta la que
      falla).
  11. Un Future se puede usar como clave porque es hashable: los objetos
      son hashables si definen __hash__ de forma consistente con __eq__; la
      clase Future no redefine __eq__, asi que usa la identidad del objeto
      (hash por id) y es inmutable en cuanto a identidad, aunque su estado
      cambie. Por eso sirve como clave aunque su contenido interno mute.

Parte D: wait
  12. wait() devuelve una tupla nombrada (done, not_done) con dos conjuntos
      de futuros: los terminados y los que no. Con FIRST_COMPLETED vuelve
      apenas hay uno terminado.
  13. Con FIRST_EXCEPTION vuelve cuando la primera tarea termina con
      excepcion (o cuando todas terminan si ninguna falla). Ver abajo.
  14. Implementado abajo en primero_que_conteste(): se queda con la primera
      respuesta. Con los otros dos futures se llama cancel(): cancela solo
      a los que todavia no empezaron; los que ya corren NO se pueden
      interrumpir y terminan igual (su resultado se descarta).
"""
import random
import time
from concurrent.futures import (FIRST_COMPLETED, FIRST_EXCEPTION,
                                ThreadPoolExecutor, as_completed, wait)

TRABAJOS = [('lenta', 0.5), ('rapida', 0.1), ('media', 0.2), ('otra', 0.4)]


def tarea(nombre, demora):
    time.sleep(demora)
    return nombre


def parte_a():
    print('=' * 62)
    print('Parte A: map contra as_completed')
    print('=' * 62)

    with ThreadPoolExecutor(4) as pool:
        t0 = time.perf_counter()
        print('  map():')
        for r in pool.map(tarea, *zip(*TRABAJOS)):
            print(f'    {r:<8} disponible a los {time.perf_counter() - t0:.2f}s')
        total_map = time.perf_counter() - t0

    with ThreadPoolExecutor(4) as pool:
        t0 = time.perf_counter()
        futuros = [pool.submit(tarea, n, d) for n, d in TRABAJOS]
        print('  as_completed():')
        for f in as_completed(futuros):
            print(f'    {f.result():<8} disponible a los {time.perf_counter() - t0:.2f}s')
        total_ac = time.perf_counter() - t0
    print(f'  total map: {total_map:.2f}s   total as_completed: {total_ac:.2f}s')


def abrir_url(url):
    """Simula una descarga; las que contienen 'rota' fallan."""
    time.sleep(random.uniform(0.05, 0.3))
    if 'rota' in url:
        raise ConnectionError(f'no se pudo abrir {url}')
    return 200


def patron_diccionario():
    print('\n' + '=' * 62)
    print('Parte C: el patron del diccionario {future: entrada}')
    print('=' * 62)
    urls = ['a.com', 'b.com', 'rota.com', 'd.com', 'e.com']
    with ThreadPoolExecutor(5) as pool:
        futuros = {pool.submit(abrir_url, u): u for u in urls}
        for f in as_completed(futuros):
            url = futuros[f]
            try:
                print(f'  {url:<10} -> {f.result()}')
            except Exception as e:
                print(f'  {url:<10} -> FALLO: {e}')
    print(f'  hash(future) funciona: {hash(next(iter(futuros))) is not None}')


def parte_d():
    print('\n' + '=' * 62)
    print('Parte D: wait()')
    print('=' * 62)

    with ThreadPoolExecutor(4) as pool:
        futuros = [pool.submit(tarea, n, d) for n, d in TRABAJOS]
        t0 = time.perf_counter()
        r = wait(futuros, return_when=FIRST_COMPLETED)
        print(f'  FIRST_COMPLETED a los {time.perf_counter() - t0:.2f}s: '
              f'tipo={type(r).__name__}, done={len(r.done)}, not_done={len(r.not_done)}')

    def falla(n):
        time.sleep(0.2)
        raise ValueError('boom')

    with ThreadPoolExecutor(4) as pool:
        futuros = [pool.submit(tarea, 'lenta', 0.6),
                   pool.submit(falla, 1),
                   pool.submit(tarea, 'media', 0.4)]
        t0 = time.perf_counter()
        r = wait(futuros, return_when=FIRST_EXCEPTION)
        print(f'  FIRST_EXCEPTION  a los {time.perf_counter() - t0:.2f}s: '
              f'done={len(r.done)}, not_done={len(r.not_done)} '
              f'(vuelve cuando falla la primera, no cuando terminan todas)')


def primero_que_conteste():
    print('\n' + '=' * 62)
    print('Parte D.14: consultar tres servidores y quedarse con el primero')
    print('=' * 62)
    servidores = [('srv-a', 0.4), ('srv-b', 0.15), ('srv-c', 0.3)]
    with ThreadPoolExecutor(3) as pool:
        futuros = [pool.submit(tarea, n, d) for n, d in servidores]
        t0 = time.perf_counter()
        listos, pendientes = wait(futuros, return_when=FIRST_COMPLETED)
        ganador = next(iter(listos)).result()
        print(f'  ganador: {ganador} a los {time.perf_counter() - t0:.2f}s')
        for f in pendientes:
            print(f'  cancel() sobre uno que ya corre -> {f.cancel()} '
                  f'(no se puede interrumpir un thread en ejecucion)')
    print('  El with espera igual a los dos restantes al salir.')


if __name__ == '__main__':
    random.seed(1)
    parte_a()
    patron_diccionario()
    parte_d()
    primero_que_conteste()

