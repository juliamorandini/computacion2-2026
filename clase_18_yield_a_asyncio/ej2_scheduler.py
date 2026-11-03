#!/usr/bin/env python3
"""Clase 18 - Ejercicio 2 (obligatorio): construir el scheduler.

Scheduler cooperativo escrito desde cero, con generadores y una deque.

Uso:
    python3 ej2_scheduler.py            # partes A, B, C y D
    python3 ej2_scheduler.py A          # una sola parte (A, B, C o D)

-----------------------------------------------------------------------
RESPUESTAS
-----------------------------------------------------------------------

Parte A: el intercalado
  1. Con tareas de 3, 2 y 4 pasos el orden es A1 B1 C1 A2 B2 C2 A3 C3 C4:
     round-robin. Cuando B termina deja de aparecer y los demas siguen.
  2. next() se llama una vez por paso mas una vez extra por tarea (la que
     levanta StopIteration): (3+2+4) + 3 = 12 llamadas. Las reanudaciones
     "utiles" (las que terminan en un yield) son 9.
  3. Una tarea sin ningun yield es una funcion comun: al llamarla corre
     entera y devuelve None, y el scheduler hace next(None) ->
     TypeError: 'NoneType' object is not an iterator. Si en cambio es un
     generador con un yield inalcanzable, corre entera de un tiron en su
     primer next() y recien ahi levanta StopIteration: no se intercala.

Parte B: la cooperacion es obligatoria
  4. Mientras la tarea egoista hace time.sleep(3) las demas NO avanzan:
     el unico hilo esta ocupado y el scheduler no recupera el control hasta
     que la tarea hace yield. Todo queda congelado 3 segundos.
  5. Con threads (clase 10) no pasaria: el sistema operativo es quien
     interrumpe un thread y le da el CPU a otro (concurrencia PREVENTIVA).
     Aca nadie interrumpe a nadie: cada tarea decide cuando ceder
     (concurrencia COOPERATIVA). Ventaja: no hay race conditions entre
     yields. Costo: una tarea mal portada frena a todas.
  6. Se llama cooperacion: "nunca bloquees el event loop". Es la misma
     regla de la clase 17: un servidor con select/selectors tambien se
     congela si un handler tarda; el loop es un solo hilo.

Parte C: agregar tiempo
  7. dormir(segundos) hace 'yield time.monotonic() + segundos': cede y le
     avisa al scheduler a que hora quiere volver.
  8. Si dormir llamara a time.sleep() bloquearia todo el hilo (igual que la
     tarea egoista). Con yield el scheduler puede atender a otras tareas
     mientras esta espera.
  9. Tres tareas que esperan 0.15 s, con 3 veces cada una: el total es
     ~0.45 s (lo que tarda UNA), no 1.35 s (la suma). Las esperas se
     solapan porque mientras una duerme corren las otras.

Parte D: yield from
  10. 'yield from dormir(espera)' delega en el subgenerador: los valores que
      dormir cede suben hasta el scheduler. Llamar solo dormir(espera)
      crea el objeto generador y no ejecuta ni una linea de su cuerpo.
  11. Sin el yield from el generador se crea y se descarta: nunca se pide
      esperar, la tarea sigue de largo y el total da ~0 s en vez de 0.45 s.
      No falla ruidosamente porque crear un generador es una operacion
      valida (analogo al warning 'coroutine was never awaited').
"""
import sys
import time
from collections import deque


# ---------------------------------------------------------------
# Parte A: scheduler basico
# ---------------------------------------------------------------

def tarea(nombre, pasos):
    for i in range(1, pasos + 1):
        print(f'  [{nombre}] paso {i}/{pasos}')
        yield
    print(f'  [{nombre}] terminada')


def scheduler(tareas):
    """Devuelve (cantidad de next() totales, reanudaciones que cedieron)."""
    pendientes = deque(tareas)
    llamadas = 0
    cedieron = 0
    while pendientes:
        t = pendientes.popleft()
        llamadas += 1
        try:
            next(t)
            cedieron += 1
            pendientes.append(t)
        except StopIteration:
            pass
    return llamadas, cedieron


def parte_a():
    print('=== Parte A: intercalado ===')
    llamadas, cedieron = scheduler([tarea('A', 3), tarea('B', 2), tarea('C', 4)])
    print(f'  next() totales: {llamadas}  (con yield: {cedieron})')

    print('\n  Tarea sin ningun yield (funcion comun):')

    def sin_yield():
        print('  [X] soy una funcion comun')

    try:
        scheduler([sin_yield()])           # sin_yield() devuelve None
    except TypeError as e:
        print(f'  TypeError: {e}')

    print('\n  Generador con yield inalcanzable: corre entero en el primer next():')

    def un_solo_turno():
        print('  [Z] hago todo de una vez')
        return
        yield                              # noqa: hace de esto un generador

    print(f'  next() totales: {scheduler([un_solo_turno(), tarea("A", 2)])[0]}')


# ---------------------------------------------------------------
# Parte B: la tarea egoista
# ---------------------------------------------------------------

def tarea_egoista(nombre):
    print(f'  [{nombre}] me pongo a calcular')
    time.sleep(3)                          # no cede el control
    print(f'  [{nombre}] listo')
    yield


def parte_b():
    print('\n=== Parte B: una tarea que no cede ===')
    t0 = time.monotonic()
    scheduler([tarea('A', 2), tarea_egoista('EGO'), tarea('B', 2)])
    print(f'  total {time.monotonic() - t0:.2f}s: A y B quedaron congeladas 3s')


# ---------------------------------------------------------------
# Parte C y D: tiempo y yield from
# ---------------------------------------------------------------

def dormir(segundos):
    yield time.monotonic() + segundos


def tarea_lenta(nombre, veces, espera=0.15, T0=None):
    for i in range(1, veces + 1):
        print(f'  [{nombre}] {i}/{veces}  (t={time.monotonic() - T0:.2f}s)')
        yield from dormir(espera)
    print(f'  [{nombre}] terminada')


def tarea_lenta_sin_yield_from(nombre, veces, espera=0.15, T0=None):
    for i in range(1, veces + 1):
        print(f'  [{nombre}] {i}/{veces}  (t={time.monotonic() - T0:.2f}s)')
        dormir(espera)                     # BUG: crea el generador y lo tira
        yield                              # cede, pero SIN pedir esperar
    print(f'  [{nombre}] terminada')


def scheduler_con_tiempo(tareas):
    pendientes = deque((0.0, t) for t in tareas)
    while pendientes:
        despertar, t = pendientes.popleft()
        if time.monotonic() < despertar:
            pendientes.append((despertar, t))
            continue
        try:
            cuando = next(t)
            pendientes.append((cuando or 0.0, t))
        except StopIteration:
            pass


def parte_c():
    print('\n=== Parte C: dormir() sin time.sleep ===')
    for corrida in range(1, 4):
        T0 = time.monotonic()
        scheduler_con_tiempo([tarea_lenta(n, 1, T0=T0) for n in 'ABC'])
        print(f'  corrida {corrida}: 3 tareas x 0.15s -> {time.monotonic() - T0:.2f}s '
              f'(suma serian 0.45s)')
    T0 = time.monotonic()
    scheduler_con_tiempo([tarea_lenta(n, 3, T0=T0) for n in 'ABC'])
    print(f'  3 tareas x 3 esperas de 0.15s -> {time.monotonic() - T0:.2f}s '
          f'(suma serian 1.35s, solapadas ~0.45s)')


def parte_d():
    print('\n=== Parte D: que pasa sin yield from ===')
    T0 = time.monotonic()
    scheduler_con_tiempo([tarea_lenta_sin_yield_from(n, 3, T0=T0) for n in 'ABC'])
    print(f'  total {time.monotonic() - T0:.2f}s: no espero nada y no hubo error')


if __name__ == '__main__':
    partes = {'A': parte_a, 'B': parte_b, 'C': parte_c, 'D': parte_d}
    elegidas = [a.upper() for a in sys.argv[1:]] or list(partes)
    for p in elegidas:
        partes[p]()
