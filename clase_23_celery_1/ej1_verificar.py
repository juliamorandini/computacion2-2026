#!/usr/bin/env python3
"""Clase 23 - Ejercicio 1 (obligatorio): el salto de escala.

Comprueba que una tarea sobrevive al proceso que la encolo.

Este script automatiza la parte B (mirar el mensaje crudo en Redis) y la
trampa del PENDING. El resto se hace a mano con los scripts de la clase
(encolar.py, consultar.py) y docker compose.

Uso (con Redis arriba: docker compose up -d, y SIN worker corriendo):
    python3 ej1_verificar.py

-----------------------------------------------------------------------
RESPUESTAS (pasos hechos en Windows; el worker se lanzo con
`python -m celery -A tareas worker -P threads --concurrency=2`, porque el
pool por defecto de Celery (prefork) no funciona en Windows)
-----------------------------------------------------------------------

Parte A: los tres pasos, sin worker
  1. Estado: PENDING. LLEN celery = 1 (la tarea esta esperando en la cola
     de Redis).
  2. Si LLEN da 0 es que ya hay un worker corriendo que se llevo la tarea.
     Me paso: tenia un worker de una prueba anterior vivo (el proceso
     python hijo seguia corriendo) y LLEN dio 0. Arreglo: matar el worker,
     FLUSHALL y volver a encolar -> LLEN = 1.
  3. Al arrancar el worker tomo la tarea en milisegundos: el log mostro
     'celery@... ready' a las 11:40:14,214 y 'Task tareas.sumar[...]
     received' a las 11:40:14,221 (7 ms despues). La cola ya tenia el
     mensaje esperandolo.
  4. consultar.py:
         state:        SUCCESS
         ready():      True
         successful(): True
         result:       5
     (el worker tardo 1.016 s: el sleep(1) de sumar).
  5. Con ThreadPoolExecutor es imposible porque un Future vive en la
     memoria del proceso que lo creo: si ese proceso termina, la tarea y su
     resultado desaparecen. Aca el trabajo y el resultado viven en Redis
     (afuera de cualquier proceso) y se encuentran con un id.

Parte B: el mensaje
  6. LINDEX celery 0 devuelve un JSON con 'body', 'headers' y 'properties'.
  7. El body esta en base64. Decodificado es:
         [[2, 3], {}, {"callbacks": null, "errbacks": null,
                       "chain": null, "chord": null}]
     o sea: args (2, 3), kwargs {} y metadatos de canvas (callbacks...).
  8. NO aparece el codigo de la funcion: en los headers solo hay
     "task": "tareas.sumar" (un NOMBRE) y el id.
  9. El worker sabe que ejecutar porque tiene su propio tareas.py: al
     arrancar registra cada @app.task con su nombre, y al recibir el mensaje
     busca ese nombre en su registro. Por la cola solo viajan nombre y
     argumentos, no codigo.
  10. Probado: un worker lanzado desde otro directorio con un tareas.py que
      NO define la tarea imprimio:
          ERROR/MainProcess] Received unregistered task of type
          'tareas.sumar'. The message has been ignored and discarded.
          Did you remember to import the module containing this task?
          (KeyError: 'tareas.sumar')
      El mensaje se descarta (y el id queda PENDING para siempre).
      Si el directorio ni siquiera tiene tareas.py el worker no arranca:
      'Unable to load celery application. The module tareas was not found'.

Parte C: el id como recibo
  11. Con el id guardado hice: bajar el worker, `docker compose down`, y
      `docker compose up -d`. Al consultar el id volvio PENDING: el
      resultado ya NO estaba.
  12. Porque el resultado vivia en la memoria/disco del contenedor de Redis
      (el backend es el mismo Redis), y el docker-compose.yml de la clase no
      tiene ningun volume: `down` borra el contenedor y con el sus datos. Si
      solo reiniciara la API o el worker (sin bajar Redis) el resultado
      seguiria (ver clase 24, parte D). Para que sobreviva haria falta
      persistencia (volume + appendonly) o un backend durable.
  13. `consultar.py --inventado` devuelve state 'PENDING', ready() False,
      result None.
  14. PENDING no distingue "esta en la cola" de "no existe": el backend solo
      guarda algo cuando la tarea termina. Para distinguirlos hay que
      guardar el id yo mismo al encolar (en una base de datos con estado
      'encolada') o mirar la cola/inspeccionar workers (LLEN, `inspect
      reserved/active`); un id que no esta en mi registro, no existe.
"""
import base64
import json

import redis

from tareas import sumar

r = redis.Redis(host='localhost', port=6399, decode_responses=True)

print('Cola antes:', r.llen('celery'))
resultado = sumar.delay(2, 3)
print(f'Encolada {resultado.id}   estado={resultado.state}')
largo = r.llen('celery')
print(f'LLEN celery = {largo}', '' if largo else '(0: hay un worker corriendo y ya se la llevo)')

if largo:
    # Buscar nuestro mensaje (el ultimo encolado es el de indice -1).
    crudo = json.loads(r.lindex('celery', -1))
    print('\nHeaders :', {k: crudo['headers'][k] for k in ('task', 'id', 'argsrepr')})
    cuerpo = base64.b64decode(crudo['body']).decode()
    print('Body    :', cuerpo)
    print('\nNo hay codigo de la funcion: solo el NOMBRE tareas.sumar y los argumentos.')

print('\nTrampa del PENDING: un id inventado')
from celery.result import AsyncResult
from tareas import app
falso = AsyncResult('id-que-no-existe-jamas', app=app)
print(f'  state={falso.state!r} ready()={falso.ready()} result={falso.result!r}')

