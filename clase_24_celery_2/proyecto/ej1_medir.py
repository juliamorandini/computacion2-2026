#!/usr/bin/env python3
"""Clase 24 - Ejercicio 1 (obligatorio): orquestar y escalar.

Ejecuta las mediciones y pruebas de las partes A a D contra el sistema de
docker compose (hay que estar en el directorio proyecto/).

Uso:
    docker compose up -d --build
    python3 ej1_medir.py A         # parte A: ps y DNS
    python3 ej1_medir.py B         # parte B: 1, 3 y 6 workers (tarda ~1 min)
    python3 ej1_medir.py C         # parte C: --scale api=2 y container_name
    python3 ej1_medir.py D         # parte D: reinicios
    python3 ej1_medir.py           # todas

-----------------------------------------------------------------------
RESPUESTAS (resultados medidos en esta maquina: Windows + Docker Desktop)
-----------------------------------------------------------------------

Nota previa: con el requirements.txt original el worker y flower
se caian al arrancar con "ModuleNotFoundError: No module named 'packaging'"
(kombu 5.6 lo importa y no lo declara). Se arreglo agregando `packaging` a
requirements.txt y reconstruyendo con --build. Sin eso /salud respondia
{"api":"ok","broker":"error: No module named 'packaging'"}.

Parte A: el sistema arriba
  1. docker compose ps:
         proyecto-api-1     proyecto-api   Up   0.0.0.0:8000->8000/tcp
         proyecto-flower-1  proyecto-flower Up  0.0.0.0:5555->5555/tcp
         proyecto-redis-1   redis:7        Up (healthy)  6379/tcp
         proyecto-worker-1  proyecto-worker Up
     Hay 4 servicios: redis, api, worker y flower.
  2. Primero arranca redis y, cuando su healthcheck (redis-cli ping cada
     3 s) da 'healthy', arrancan api, worker y flower (se ve en la salida
     'Container proyecto-redis-1 Waiting ... Healthy'). La API (y el worker
     y flower) esperan por 'depends_on: condition: service_healthy': que el
     contenedor exista no implica que Redis ya acepte conexiones, y sin
     eso podrian arrancar, intentar conectarse y fallar.
  3. Publican puertos al host 2 servicios: api (8000) y flower (5555).
     Redis no, porque solo lo usan los otros servicios desde la red
     interna de compose; publicarlo lo expondria sin necesidad (y sin
     contrasena) a la maquina y a la red.
  4-5. gethostbyname('redis') -> 172.22.0.2 (IP de la red interna de Docker
     del proyecto; el numero exacto cambia). No es una IP de mi maquina:
     es la IP del contenedor de Redis en la red virtual. El DNS interno de
     Docker resuelve el nombre del servicio.

Parte B: medir el escalado (6 tareas de 4 s; cada worker tiene
--concurrency=2, o sea 2 slots)
  6. 1 worker (2 slots): 3 rondas de 4 s -> 12.12 s
  7-8. 3 workers (6 slots): 4.10 s (otra corrida dio 8.11 s: el primer worker
       que se conecto se llevo mas de 2 tareas por el prefetch y el reparto
       quedo desparejo). Proporcion 12.12 / 4.10 = ~3x, igual a la cantidad
       de workers y de slots (6/2).
  9. No: no se modifico ninguna linea de Python ni de compose entre las
     mediciones; solo se cambio `--scale worker=N`.
  10. 6 workers (12 slots): 4.10 s, NO mejora respecto de 3: hay solo 6
      tareas, y 6 slots ya alcanzan para correrlas todas a la vez. Los
      slots de mas quedan ociosos; el piso es lo que tarda UNA tarea (4 s).

Parte C: lo que no se puede escalar
  11. docker compose up -d --scale api=2 falla con
        'Bind for 0.0.0.0:8000 failed: port is already allocated'
      (la segunda replica intenta publicar el mismo puerto del host).
  12. El worker no publica ningun puerto: nadie le habla, el solo se
      conecta a Redis y saca trabajo de la cola, asi que N copias no chocan.
      La API si publica el 8000, y un puerto del host puede tener un solo
      dueno.
  13. Haria falta algo adelante que reparta el trafico: un balanceador /
      reverse proxy (nginx, traefik) que escuche en el 8000 y reparta entre
      las replicas, y que las replicas NO publiquen puerto (solo `expose`).
  14. Con container_name: mi_worker, `--scale worker=3` falla:
        'The "worker" service is using the custom container name
         "mi_worker". Docker requires each container to have a unique name.
         Remove the custom name to scale the service'
      Un nombre de contenedor es unico en Docker: tres contenedores no
      pueden llamarse igual.

Parte D: sobrevivir a los reinicios
  15-17. Se encolo esperar(60) con POST /trabajos, se hizo `docker compose
      restart api` y se consulto el id: SIGUE ahi (estado STARTED). El
      estado vive en Redis (el backend), no en la memoria de la API; la API
      es solo una vista, y el worker seguia ejecutando la tarea.
  18. Al reiniciar el worker a mitad de la tarea (docker compose restart
      worker; docker lo mata a los 10 s) la tarea quedo en STARTED durante
      todo lo que se observo (80 s despues, mas de lo que dura la tarea): no
      termino y no se re-ejecuto todavia. Con acks_late=True el mensaje no
      se confirmo (ack) porque la tarea no termino, asi que sigue "sin
      confirmar" en Redis, y recien se vuelve a entregar cuando vence el
      visibility_timeout del transporte Redis (1 hora por defecto) o si el
      worker cierra la conexion limpiamente. Por eso con acks_late las
      tareas tienen que ser idempotentes: puede ejecutarse dos veces.
      (Sin acks_late el ack se hace al recibirla: si el worker muere, la
      tarea se pierde sin ejecutarse del todo.) Ojo: STARTED engana, el
      estado no se actualiza cuando muere el worker.
  19. Con `docker compose down` y `up`, un id viejo vuelve PENDING: el
      resultado/estado se perdio porque Redis no tiene volume (los datos
      viven dentro del contenedor, que `down` borra). No es lo mismo que
      reiniciar. Persistir requiere un volume en /data.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
API = os.environ.get('API', 'http://localhost:8000')

CODIGO_MEDIR = """
import time
from celery import group
from tareas import esperar
t0 = time.perf_counter()
group(esperar.s(4) for _ in range(6)).apply_async().get(timeout=90)
print(f'{time.perf_counter()-t0:.2f}s')
"""


def sh(*args, **kw):
    r = subprocess.run(args, cwd=AQUI, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', **kw)
    return (r.stdout + r.stderr).strip(), r.returncode


def dc(*args):
    return sh('docker', 'compose', *args)


def http(metodo, ruta, cuerpo=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(API + ruta, data=datos, method=metodo,
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def esperar_workers(n, timeout=60):
    """Espera hasta que /salud vea n workers registrados."""
    fin = time.time() + timeout
    while time.time() < fin:
        try:
            _, j = http('GET', '/salud')
            if len(j.get('workers', [])) >= n:
                return len(j['workers'])
        except Exception:
            pass
        time.sleep(1)
    return -1


def medir():
    salida, _ = dc('exec', '-T', 'api', 'python', '-c', CODIGO_MEDIR)
    return salida.splitlines()[-1]


def parte_a():
    print('=== Parte A ===')
    print(dc('ps')[0])
    print(f'  servicios: {len(dc("config", "--services")[0].split())}')
    print('  DNS:', dc('exec', '-T', 'api', 'python', '-c',
                       "import socket; print(socket.gethostbyname('redis'))")[0])


def parte_b():
    print('\n=== Parte B: 6 tareas de 4 s ===')
    for n in (1, 3, 6):
        dc('up', '-d', '--scale', f'worker={n}')
        vistos = esperar_workers(n)
        time.sleep(2)
        print(f'  {n} worker(s) ({n * 2} slots, vistos {vistos}): {medir()}')
    dc('up', '-d', '--scale', 'worker=1')
    esperar_workers(1)


def parte_c():
    print('\n=== Parte C ===')
    salida, rc = dc('up', '-d', '--scale', 'api=2')
    print('  --scale api=2 ->', 'rc', rc)
    print('   ', '\n    '.join(l for l in salida.splitlines()
                               if 'rror' in l or 'ailed' in l or 'llocated' in l)[:400])

    # container_name en el worker, con un override temporal (no toco el compose)
    override = 'services:\n  worker:\n    container_name: mi_worker\n'
    with tempfile.NamedTemporaryFile('w', suffix='.yml', delete=False, dir=AQUI) as f:
        f.write(override)
        ruta = f.name
    try:
        salida, rc = dc('-f', 'docker-compose.yml', '-f', os.path.basename(ruta),
                        'up', '-d', '--scale', 'worker=3')
        print('  container_name + --scale worker=3 -> rc', rc)
        print('   ', salida.splitlines()[-1][:300] if salida else '')
    finally:
        os.unlink(ruta)
    dc('up', '-d', '--scale', 'worker=1', '--remove-orphans')
    esperar_workers(1)


def parte_d():
    print('\n=== Parte D ===')
    codigo, r = http('POST', '/trabajos', {'tipo': 'esperar', 'dato': '60'})
    tid = r['id']
    print(f'  encolada esperar(60): {r}')
    print('  restart api ->', dc('restart', 'api')[1])
    time.sleep(5)
    print('  consulta tras reiniciar la API:', http('GET', f'/trabajos/{tid}')[1])

    print('\n  reiniciando el worker a mitad de la tarea (acks_late=True)...')
    dc('restart', 'worker')
    for i in range(8):
        time.sleep(10)
        print(f'  D18 +{(i + 1) * 10:>2}s:', http('GET', f'/trabajos/{tid}')[1].get('estado'))
    print('  consulta final:', http('GET', f'/trabajos/{tid}')[1])

    print('\n  docker compose down + up y consulta del id viejo...')
    dc('down')
    dc('up', '-d')
    esperar_workers(1)
    print('  ->', http('GET', f'/trabajos/{tid}')[1])


if __name__ == '__main__':
    partes = {'A': parte_a, 'B': parte_b, 'C': parte_c, 'D': parte_d}
    for p in [a.upper() for a in sys.argv[1:]] or partes:
        partes[p]()
