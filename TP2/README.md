# TP2 - Plataforma de Tareas Distribuidas

Computación II — Universidad de Mendoza — 2026

## 1. Descripción y uso

Es un servicio HTTP al que se le encargan trabajos. El `POST` los encola y responde enseguida con un `id`; un pool de workers corrutina los ejecuta de forma concurrente, y el cliente consulta después el estado y el resultado. Todo corre en un solo proceso y un solo hilo con `asyncio`. El único trabajo que sale del event loop es el CPU-bound, que va a un `ProcessPoolExecutor`.

Hay tres tipos de tarea:

| Tipo | Naturaleza | Parámetros | Resultado |
|------|-----------|-----------|-----------|
| `descargar` | I/O-bound | `urls`: de 1 a 100 URLs `http://` o `https://` | por URL: `status`, `bytes`, `segundos` (o `error`) |
| `hashear` | CPU-bound | `texto` (hasta 10.000 caracteres), `iteraciones` de 1 a 100.000.000 | SHA-256 aplicado N veces |
| `esperar` | I/O simulado | `segundos` de 0 a 3600 | los segundos esperados |

Todas aceptan además un `timeout` opcional en segundos, mayor que 0 y hasta 3600. Si no se manda, se usa `TIMEOUT_DEFAULT` (30 s). Los topes existen para que una sola tarea no pueda pedir trabajo ilimitado: sin tope, un POST con 50.000 URLs lanzaría 50.000 corrutinas dentro de un worker y esquivaría el límite de la cola.

Si en `descargar` falla alguna URL, la tarea queda `completada` y esa URL trae su `error`. Si fallan **todas**, la tarea queda `fallida`, porque no hizo nada útil.

### Cómo levantarlo

```bash
cd TP2
docker compose up --build
```

La API queda en `http://localhost:8000`, con la documentación interactiva en `http://localhost:8000/docs`. El compose también levanta `servidor_lento`, un servidor HTTP de prueba hecho con asyncio puro. Responde `GET /demora?s=X` después de esperar X segundos, y sirve para probar las descargas sin depender de internet. Desde la API se lo alcanza como `http://servidor_lento:9000`, y desde el host como `localhost:9000`.

### Ejemplos con curl

```bash
# Encolar una tarea de cada tipo (el POST responde enseguida: {"id": ..., "estado": "pendiente"})
curl -X POST localhost:8000/tareas -H 'Content-Type: application/json' \
     -d '{"tipo": "esperar", "params": {"segundos": 30}}'

curl -X POST localhost:8000/tareas -H 'Content-Type: application/json' \
     -d '{"tipo": "descargar", "params": {"urls": [
           "http://servidor_lento:9000/demora?s=1",
           "http://servidor_lento:9000/demora?s=1",
           "https://example.com"]}}'

curl -X POST localhost:8000/tareas -H 'Content-Type: application/json' \
     -d '{"tipo": "hashear", "params": {"texto": "hola", "iteraciones": 5000000}}'

# Timeout propio: esta tarea termina en "fallida" con "timeout de 1.0s excedido"
curl -X POST localhost:8000/tareas -H 'Content-Type: application/json' \
     -d '{"tipo": "esperar", "params": {"segundos": 5}, "timeout": 1}'

# Consultar
curl localhost:8000/tareas                     # todas
curl "localhost:8000/tareas?estado=ejecutando" # filtradas por estado
curl localhost:8000/tareas/<id>                # una (404 si no existe)
curl localhost:8000/estadisticas               # totales por estado, tiempos promedio (ejecución y espera en cola), workers ocupados

# Cancelar (sirve tanto en pendiente como en ejecución; 409 si ya terminó)
curl -X DELETE localhost:8000/tareas/<id>

# Apagado ordenado: drena, vuelca estado_<timestamp>.json y el próximo arranque lo informa por log
docker compose stop api
docker compose start api && docker compose logs api | grep "Volcado previo"
```

El `DELETE` responde con el estado final: `{"id": ..., "estado": "cancelada"}`. Sobre una tarea en ejecución, espera a que el `asyncio.Task` de la tarea termine de verdad (milisegundos) antes de responder.

Respuestas de error:
- **422** si la tarea es inválida: un tipo desconocido, `urls: []`, una URL que no es `http(s)`, `iteraciones: 0`, valores fuera de los topes, `Infinity`/`NaN`, o un campo desconocido (un typo como `"segundo"` en vez de `"segundos"` no se ignora). También si `?estado=` no es uno de los cinco estados.
- **503** si la cola está llena o el servidor se está apagando.
- **404** si la tarea no existe.
- **409** si se intenta cancelar una tarea que ya terminó.

### Tests

```bash
cd TP2
docker compose run --rm tests
```

Son 56 tests con `pytest` + `pytest-asyncio` y corren dentro de un contenedor, así que no hace falta instalar nada. Levantan la app con su `lifespan` real (cola, workers, pool de procesos) y le hablan con `httpx.ASGITransport`, sin abrir un socket. Las descargas van contra un servidor HTTP falso (`httpx.MockTransport`) para no depender de la red. Cubren:

- `test_api_validacion.py`: el POST responde en < 50 ms aunque la tarea dure 10 s, todos los casos de 422, el filtro por estado, 404 y `/estadisticas`.
- `test_concurrencia_y_cpu.py`: 5 descargas de 0.3 s tardan < 0.6 s, el hash en bloques da el mismo resultado que el SHA-256 iterado, un `GET` no pasa de 50 ms durante un hash pesado, y **sin executor** el loop se atrasa más de 200 ms (M2 como test).
- `test_cancelacion_y_timeout.py`: DELETE de una pendiente, DELETE a mitad de cada uno de los tres tipos (verifica que queden el worker libre, el semáforo completo y ningún Task huérfano), 409 y timeouts.
- `test_backpressure_y_apagado.py`: 503 con la cola llena sin dejar tareas fantasma, el apagado ordenado con su volcado, y el reporte del volcado previo al arrancar.

### Configuración

Todo se configura por variables de entorno. En el compose se pueden sobreescribir desde el host, por ejemplo `WORKERS=16 docker compose up -d api`.

| Variable | Default | Qué controla |
|----------|---------|--------------|
| `WORKERS` | 4 | corrutinas worker del pool |
| `COLA_MAX` | 100 | tamaño máximo de la `asyncio.Queue`; pasado ese número, el POST devuelve 503 |
| `PROCESOS_CPU` | 2 | procesos del `ProcessPoolExecutor` |
| `MAX_DESCARGAS_SIMULTANEAS` | 10 | tope del semáforo global de conexiones HTTP |
| `TIMEOUT_DEFAULT` | 30 | timeout por tarea, si el POST no manda uno |
| `LIMITE_APAGADO` | 10 | cuánto se espera a las tareas en curso al apagar |
| `HASH_EN_EXECUTOR` | 1 | `0` hace el hash dentro de la corrutina. **Existe solo para la medición M2** |

### Estructura

```
TP2/
├── src/
│   ├── main.py          # lifespan (crea y cierra recursos), señales, arranque de uvicorn
│   ├── api.py           # los 5 endpoints
│   ├── modelos.py       # Estado (Enum), TareaIn con validación por tipo, Tarea interna
│   ├── registro.py      # dict id -> Tarea y las transiciones de estado
│   ├── pool.py          # asyncio.Queue + N workers, Task interno, timeout, cancelación
│   ├── tareas.py        # descargar / hashear / esperar
│   ├── cpu.py           # sha256_bloque (top-level, picklable) e initializer de los hijos
│   ├── persistencia.py  # volcado estado_<timestamp>.json y reporte al arrancar
│   └── config.py        # variables de entorno
├── tests/               # pytest + pytest-asyncio (docker compose run --rm tests)
└── mediciones/          # servidor_lento.py, medir_*.py, correr_mediciones.sh, resultados/
```

## 2. Diagrama de arquitectura

```
                         un proceso, un hilo, un event loop
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                                                                             │
  │  Cliente ── POST /tareas ──> api.py ──┬─ registro.registrar()  (pendiente)  │
  │     ^                        (FastAPI) └─ cola.put_nowait(id) (503 si llena)│
  │     │                                         │                             │
  │     │ GET /tareas, /estadisticas              v                             │
  │     └──────────────── registro <──── ┌──────────────────┐                   │
  │                       (dict en       │  asyncio.Queue   │                   │
  │                        memoria)      └────────┬─────────┘                   │
  │                          ^                    │ await cola.get()            │
  │                          │       ┌────────────┼────────────┐                │
  │                          │       v            v            v                │
  │                          │   worker-0     worker-1  ...  worker-N-1         │
  │                          │       │ crea un asyncio.Task interno por tarea   │
  │                          │       │ dentro de asyncio.timeout(t)             │
  │                          └───────┤ (ejecutando / completada / fallida /     │
  │                     marca estado │  cancelada)                              │
  │                                  │                                          │
  │          ┌───────────────────────┼─────────────────────────┐                │
  │          v                       v                         v                │
  │      esperar               descargar                    hashear             │
  │   asyncio.sleep     gather + Semaphore +        run_in_executor por bloques │
  │                     httpx.AsyncClient (uno)                │                │
  └────────────────────────────┼───────────────────────────────┼────────────────┘
                               v                               v
                     servidor_lento / internet        ProcessPoolExecutor
                                                      (PROCESOS_CPU hijos)
```

### Flujo de una tarea

```
 POST ──> pendiente ──(un worker la saca de la cola)──> ejecutando ──┬──> completada
             │                                                       ├──> fallida   (excepción o timeout, con motivo)
             │ DELETE                                                └──> cancelada (DELETE o apagado)
             v
          cancelada  (el worker la saltea cuando la saca de la cola)
```

1. **`POST /tareas`**. Pydantic valida el cuerpo; si es inválido devuelve 422 y la tarea nunca entra. Si la cola está llena devuelve 503. Si no, la tarea se registra como `pendiente`, su id entra a la cola con `put_nowait` y se responde. En el endpoint no hay ningún `await` del trabajo, así que la respuesta tarda milisegundos (M3: 2-3 ms con la API tranquila).
2. **Un worker** hace `await cola.get()`. Si la tarea ya estaba `cancelada`, la saltea. Si no, la marca `ejecutando` y crea un `asyncio.Task` interno que corre la tarea dentro de `asyncio.timeout(t)`.
3. **Al terminar**, el worker la marca `completada`, `fallida` (con el motivo) o `cancelada`, y vuelve a `cola.get()`.

## 3. Decisiones de diseño

### ¿Por qué `asyncio.Queue` y no `queue.Queue`?

Porque `queue.Queue.get()` bloquea **el hilo**, y en este programa hay un solo hilo: el del event loop. Un worker esperando en una `queue.Queue` vacía congelaría la API completa, y con N workers sería todavía peor. En cambio, `await asyncio.Queue.get()` suspende **solo esa corrutina**: el loop sigue atendiendo HTTP y a los otros workers, y despierta al worker cuando alguien hace `put`.

`asyncio.Queue` no es thread-safe, pero tampoco necesita serlo: productores (los endpoints) y consumidores (los workers) corren todos en el mismo hilo. Por eso `queue.Queue` paga un `Lock` interno que acá no aporta nada. `asyncio.Queue` además da backpressure: con `maxsize=COLA_MAX`, `put_nowait` falla y el POST devuelve 503 en vez de acumular memoria sin límite.

### ¿Por qué el pool no necesita un `Lock`?

En asyncio el cambio de contexto solo ocurre en un `await`. Un worker no puede ser interrumpido en mitad de una línea por otro worker ni por un endpoint, como pasaría con threads. Entonces alcanza con que **ninguna sección crítica tenga un `await` en el medio**, y así está escrito. Por ejemplo, en el worker:

```python
self._registro.marcar_ejecutando(tarea_id)   # lee y cambia el estado
self._ocupados += 1                          # sin await entre medio: atómico para el loop
```

Lo mismo en el POST: entre `if _cola.full()`, `registrar()` y `put_nowait()` no hay ningún `await`, así que nadie puede llenar la cola entre el chequeo y el `put`. Las únicas excepciones serían código en otros hilos o procesos, y ese código (`sha256_bloque` en los hijos, el volcado en `to_thread`) no toca el registro: recibe datos y devuelve un resultado.

### ¿Cómo evito que una tarea CPU-bound congele la API?

`sha256_bloque` es Python puro calculando, sin ningún `await`. Si corre dentro de una corrutina, el loop no recupera el control hasta que termina, y durante ese lapso no se atiende ningún request. La medición M2 lo muestra: **2.4 s de mediana por GET sin executor, contra 1.5 ms con executor**.

La solución es `loop.run_in_executor(pool_cpu, sha256_bloque, h, n)`, que manda el cómputo a otro proceso y devuelve un future al que el worker le hace `await`. El loop queda libre mientras tanto. Hay dos decisiones encima de eso:

- **Procesos y no threads (`to_thread`)**. Con threads el loop no se congelaría, porque el GIL se suelta cada tanto, pero varias tareas `hashear` simultáneas se ejecutarían de a una, porque solo un thread corre bytecode Python a la vez. Con `ProcessPoolExecutor` cada hijo tiene su propio intérprete y su propio GIL. M3 lo muestra: 32 hashes tardan 10.4 s con 1 proceso y 1.5 s con 16.
- **En bloques de 100.000 iteraciones**. Un future de proceso que ya empezó **no se puede cancelar**: `cancel()` devuelve `False` y el hijo sigue calculando hasta el final. Si el hash fuera un solo `run_in_executor` de 20 millones de iteraciones, un DELETE o un timeout recién tendría efecto cuando el hijo terminara. Partido en bloques, hay un `await` cada ~35 ms, y la cancelación se nota en el siguiente. Las funciones trabajan con bytes y no con hex, así que encadenar bloques da exactamente el mismo hash que una corrida entera.

`sha256_bloque` vive a nivel de módulo en `cpu.py` porque el executor la manda a los hijos con `pickle`, y una lambda o una función anidada no se pueden picklear. El `initializer` del pool les pone `SIGINT` en `SIG_IGN` a los hijos: así un Ctrl+C lo maneja solo el padre, que es quien decide cuándo cerrar el pool.

### ¿Cómo implementé la cancelación y qué pasa con los recursos a medio usar?

El worker no ejecuta la tarea directamente: crea un `asyncio.Task` interno y lo guarda en la tarea. `DELETE` cancela **ese Task**, no al worker, que sigue vivo y vuelve a la cola.

- **Tarea pendiente**: el DELETE solo la marca `cancelada`. Cuando un worker la saca de la cola, ve el estado y la saltea. No hace falta buscarla dentro de la cola.
- **Tarea en ejecución**: `task_interno.cancel()` hace que se lance `CancelledError` en el `await` en el que esté parada la tarea:
  - `esperar`: el error sale de `asyncio.sleep` y no queda nada más que liberar.
  - `descargar`: el error sale del `gather`, y `gather` cancela a cada una de las descargas hijas. Cada hija está dentro de `async with semaforo:` y de `async with cliente.stream(...)`. Al propagarse el error se ejecutan los `__aexit__`: el stream cierra la conexión HTTP y el semáforo libera su lugar. No quedan corrutinas huérfanas, sockets abiertos ni lugares del semáforo tomados. El cliente httpx es uno solo y compartido, así que no se cierra por cada tarea: se cierra en el apagado.
  - `hashear`: el error sale del `await` del bloque en curso. Ese bloque termina en el hijo (~35 ms) y su resultado se descarta. No se manda el siguiente, y el proceso del pool queda libre para otra tarea.
- **¿Cancelaron la tarea o al worker?** Las dos cosas llegan como el mismo `CancelledError`. Para distinguirlas, el worker usa `asyncio.current_task().cancelling()`. Si es mayor que cero, lo cancelaron a él (apagado): marca la tarea `cancelada` con el motivo "apagado del sistema" y **relanza** el error, porque tragarse un `CancelledError` propio rompe el protocolo de cancelación de asyncio. Si es cero, fue un DELETE: marca `cancelada` y sigue con la siguiente tarea.
- **Timeout**: `async with asyncio.timeout(t)` cancela por dentro y lo convierte en `TimeoutError`. Se captura y la tarea queda `fallida` con el motivo "timeout de Xs excedido". Libera los recursos por el mismo camino que la cancelación.
- **La respuesta del DELETE**: `cancel()` no corta nada en el momento, solo pide la cancelación. Por eso el endpoint hace `await asyncio.wait([task], timeout=1)` antes de responder. Es un `await`, así que no bloquea el loop, y al volver la tarea ya está `cancelada` y sus recursos ya se liberaron. No hay carrera con el worker: el worker hacía `await` de ese mismo Task desde antes, así que su callback está primero en la cola del loop y marca `cancelada` antes de que el endpoint se despierte.

Está verificado a mano y con tests. Un DELETE a mitad de un `esperar 30`, de un `descargar` lento o de un `hashear` de 100 millones de iteraciones deja la tarea `cancelada` en unos 10 ms. Los tests además comprueban que después del DELETE el worker está libre, el semáforo tiene todos sus lugares y no queda ningún `asyncio.Task` vivo de esa tarea, ni el interno ni los hijos del `gather`.

### ¿Qué pasa si un worker lanza una excepción no capturada?

Dentro de la ejecución de la tarea no puede pasar: el worker la envuelve en `except Exception`. La tarea queda `fallida` con `repr(excepción)`, se loguea el traceback y el worker sigue con la siguiente. El `finally` siempre descuenta `ocupados` y llama a `task_done()`, así que tampoco quedan contadores desfasados.

Si igual se escapara algo del bucle del worker (un bug en el propio worker y no en la tarea), el `asyncio.Task` del worker terminaría con la excepción guardada adentro. Sin ningún mecanismo extra, eso pasa **en silencio**: nadie hace `await` de los workers hasta el apagado, así que nadie lee la excepción. El pool queda con un worker menos y lo único que se ve es que las tareas tardan más. Por eso cada worker tiene un `add_done_callback` que loguea con nivel ERROR si un worker termina con excepción. Una mejora pendiente es que además lance un worker de reemplazo (ver Limitaciones).

### Otras decisiones

- **`httpx.AsyncClient` para las descargas.** Tiene la misma API que `requests`, pero cada operación de red es un `await`, y el modo streaming con `async with` garantiza cerrar la conexión cuando hay cancelación. Uso **un solo cliente** creado en el `lifespan` y no uno por tarea: así se reutiliza el pool de conexiones y el keep-alive, y siempre lleva un timeout (30 s) para que un servidor colgado no deje una tarea esperando para siempre.
- **Semáforo global de descargas.** Sin un tope, una tarea con 10.000 URLs abriría 10.000 sockets a la vez y agotaría los descriptores de archivo. M1 muestra su costo: con `MAX_DESCARGAS_SIMULTANEAS=10`, 20 URLs salen en dos tandas (1.83 s); con 20, en una sola (1.19 s).
- **Uvicorn con un solo proceso.** El estado vive en un `dict` en memoria: con varios workers de uvicorn, cada proceso tendría su propio registro, y un `GET` podría no encontrar una tarea creada por otro proceso.
- **Apagado ordenado.** `loop.add_signal_handler` (o `signal.signal` en Windows fuera de Docker) recibe SIGTERM/SIGINT y le pide a uvicorn que deje de escuchar. Después, el `lifespan` hace lo siguiente:
  1. Pone `aceptando = False`, así que el POST devuelve 503.
  2. Vacía la cola, de modo que las pendientes **no se ejecutan** y quedan en el volcado como `pendiente`.
  3. Pone un centinela `object()` por worker y les da `LIMITE_APAGADO` segundos para terminar lo que tienen en curso. Poner los centinelas y esperar a los workers corren **juntos** bajo un mismo `asyncio.timeout`: si la cola es más chica que el pool y todos los workers están ocupados, el `put` del centinela espera a que alguno se libere, y fuera del timeout el apagado podía quedar colgado para siempre.
  4. Cancela a los que no llegaron (sus tareas quedan `cancelada` con el motivo "apagado del sistema").
  5. Escribe `estado_<YYYYmmdd_HHMMSS>.json` desde un thread (`asyncio.to_thread`).
  6. Cierra httpx y el pool de procesos.

  En Docker, el `CMD` en forma exec hace que Python sea el PID 1 y reciba la señal directamente, y `stop_grace_period: 15s` es mayor que `LIMITE_APAGADO`, porque con el default de 10 s Docker mataría el proceso con SIGKILL a mitad del drenado. El volcado se guarda en un volumen, así que sobrevive al contenedor. Al arrancar, se loguea el último volcado con los conteos por estado. No se restaura, porque la consigna pide solo reportarlo.
- **Un bug que encontré en el camino.** Al principio uvicorn se arrancaba con `uvicorn.Config(app='main:app')`. Con el string, uvicorn **importa `main.py` por segunda vez**, como un módulo llamado `main`, distinto del `__main__` que se estaba ejecutando. El handler de señal y la referencia al servidor quedaban en módulos distintos: la señal se logueaba pero nadie le avisaba a uvicorn, y Docker terminaba matando el proceso sin volcado. Se arregló pasando el objeto `app` directamente.
- **Bugs que encontraron los tests.** Escribí primero los tests de lo que debería pasar y los corrí contra el código existente. Fallaron estos casos, que después corregí:
  - **Apagado colgado con `COLA_MAX < WORKERS`.** Los centinelas se ponían con `await cola.put()` antes de que empezara a correr el límite de tiempo. Si la cola no tenía lugar y todos los workers estaban ocupados, el apagado no terminaba nunca, Docker mataba el proceso con SIGKILL y no había volcado.
  - **`_aceptando` nunca volvía a `True`.** Después del primer apagado, una app levantada otra vez en el mismo proceso rechazaba todo con 503. En producción no pasa, porque el proceso muere, pero con los tests apareció enseguida.
  - **Validación permisiva.** `{"segundo": 10}` con el typo devolvía 201 y esperaba 1 s, el default, sin avisar. Se arregló con `extra='forbid'`. Al agregar el rechazo de `Infinity`, apareció otro bug: el handler de 422 de FastAPI devuelve el valor recibido dentro del JSON, JSON no admite `Infinity`, y el cliente recibía **500** en vez de 422. Lo resuelve un handler propio que manda esos valores como texto.
  - **El DELETE respondía `"cancelando"`**, que no es uno de los cinco estados. Un segundo DELETE inmediato también devolvía 200, porque la tarea seguía figurando `ejecutando`.

### Preguntas de la corrección

- **"¿Dónde podría bloquear el event loop?"** Encontré estos puntos:
  1. `hashear` con `HASH_EN_EXECUTOR=0`. Está a propósito, solo para M2.
  2. `GET /tareas` sin filtro, porque serializa todo el registro en el hilo del loop. Medido: 2.7 ms con 100 tareas, 18 ms con 1.000 y **164 ms con 10.000**. Crece lineal y sin tope, porque el registro nunca se purga.
  3. `/estadisticas`, que recorre todo el registro en cada llamada. Es más liviano que el anterior porque no serializa cada tarea, pero también es lineal.
  4. El logging a stdout es sincrónico, aunque en la práctica cuesta microsegundos.

  El volcado de disco no bloquea porque va con `to_thread`.
- **"¿Qué pasa si cancelo una tarea a mitad de una descarga?"** Ver la sección de cancelación: `CancelledError` en el `await` de httpx, `gather` cancela a las hijas, y los `async with` cierran el stream y liberan el semáforo. La tarea queda `cancelada` en menos de un segundo.
- **"¿Qué diferencia hay entre `gather` y un `for` con `await`?"** El `for` no lanza la segunda descarga hasta que termina la primera, así que los tiempos se suman. `gather` crea todas las corrutinas a la vez: mientras una espera la red, el loop avanza las otras, y el total es el de la más lenta. Medido: **13.59 s contra 1.17 s** (M1).
- **"¿Por qué `time.sleep()` en una corrutina es un bug y `asyncio.sleep()` no?"** `time.sleep` duerme **el hilo**, y con él el loop entero: nadie más corre durante ese lapso. Es exactamente el efecto que M2 mide con el hash sin executor. `asyncio.sleep` es un `await`: suspende solo esa corrutina, le devuelve el control al loop y este la despierta cuando vence el plazo. `grep -rn "time.sleep" src/` no devuelve código.
- **"Si te mando 10.000 tareas de golpe, ¿qué se rompe primero?"** Medido en M3: no se rompe nada, pero se satura en este orden:
  1. **El propio event loop atendiendo HTTP.** 10.000 POSTs simultáneos se procesan de a uno en un solo hilo, a unos 400 por segundo, y la mediana del POST sube a ~16.7 s.
  2. **La cola.** Con `COLA_MAX=100` entran 192 tareas y 9.808 reciben 503. Es un rechazo controlado: la memoria no crece y no hubo ni un error de conexión.

  Si se sube `COLA_MAX`, entran todas, pero aparece lo siguiente: el registro crece sin límite y cada `GET /tareas` congela el loop más tiempo (164 ms con 10.000).

## 4. Mediciones

Todos los números salen de mi máquina: Intel Core i5-14400 (10 núcleos físicos, 6 de rendimiento y 4 de eficiencia, 16 hilos), Docker Desktop en Windows 11, y el contenedor ve 16 CPUs. Las descargas van contra `servidor_lento` dentro de la red del compose, no contra internet, para que los números no dependan de la conexión.

Para reproducirlas (tarda unos 10 minutos y rearranca la API con la configuración de cada corrida):

```bash
cd TP2
bash mediciones/correr_mediciones.sh
```

Las tablas completas quedan en [mediciones/resultados/](mediciones/resultados/). El cliente de las mediciones corre en el servicio `mediciones` del compose, que es Python con httpx, así que no hay que instalar nada en el host.

### M1 — Concurrencia I/O: 20 descargas secuenciales contra concurrentes

[`medir_io.py`](mediciones/medir_io.py) descarga 20 URLs con demoras distintas, de 0.20 a 1.15 s. La suma de las demoras es 13.50 s y la más lenta tarda 1.15 s. Mediana de 3 corridas:

| Modo | Mediana | Mín | Máx |
|------|--------:|----:|----:|
| Secuencial (`for` + `await`) | **13.59 s** | 13.58 s | 13.59 s |
| Concurrente (`asyncio.gather`) | **1.17 s** | 1.16 s | 1.17 s |
| **Speedup** | **11.7x** | | |

De punta a punta, como una tarea `descargar` de la API con las mismas 20 URLs:

| `MAX_DESCARGAS_SIMULTANEAS` | Tiempo de la tarea | Descarga más lenta |
|---|---:|---:|
| 10 (default) | 1.83 s | 1.15 s |
| 20 | 1.19 s | 1.17 s |

**Interpretación.** El secuencial tarda la **suma** de las demoras (13.5 s, más ~4 ms por request de overhead). El concurrente tarda lo que **la más lenta** (1.15 s, más ~20 ms): las 20 esperas de red se solapan, porque mientras una corrutina está parada en el `await` de su socket, el loop avanza las demás. El speedup no es 20x porque está acotado por la proporción suma/máximo, que acá es 13.5 / 1.15 ≈ 11.7. Es exactamente lo que se midió.

Dentro de la API aparece el semáforo. Con 10 lugares, las 20 descargas salen en dos tandas y la tarea tarda 1.83 s. Con 20 lugares sale todo junto y tarda 1.19 s, lo mismo que el `gather` directo. El semáforo es una decisión a propósito: cambia algo de latencia en tareas grandes por no agotar los descriptores de archivo.

### M2 — El event loop bloqueado

[`medir_bloqueo.py`](mediciones/medir_bloqueo.py) encola un `hashear` de 14 millones de iteraciones (~4.7 s) y, mientras corre, lanza un `GET /tareas` cada 50 ms. Cada GET sale a su horario aunque el anterior no haya vuelto, así se ve cuántos se acumulan. Antes mide 40 GETs con la API sin trabajo como referencia.

| Modo | Momento | GETs | Mediana | p95 | Máx |
|------|---------|-----:|--------:|----:|----:|
| **Sin executor** (`HASH_EN_EXECUTOR=0`) | API ociosa | 40 | 1.7 ms | 2.8 ms | 3.8 ms |
| | **Durante el hash** | 94 | **2389 ms** | **4463 ms** | **4692 ms** |
| **Con executor** (`HASH_EN_EXECUTOR=1`) | API ociosa | 40 | 2.0 ms | 3.2 ms | 4.5 ms |
| | **Durante el hash** | 98 | **1.5 ms** | **2.1 ms** | **3.7 ms** |

**Interpretación.** Sin executor, el loop queda dentro de `sha256_bloque` durante los ~4.7 s del hash. Los GETs llegan al socket, pero nadie los lee: el loop no vuelve a `select`/`epoll` hasta que el cálculo termina. Cuando por fin vuelve, los atiende todos de golpe. Por eso las latencias forman una escalera: el GET que llegó al principio esperó ~4.7 s, el del medio ~2.4 s (la mediana) y el último casi nada. Durante esos 4.7 s la API estuvo **completamente muerta para todos los clientes**, no solo para el que pidió el hash.

Con executor, el GET durante el hash tarda lo mismo que con la API ociosa (1.5 ms contra 2.0 ms; la diferencia es ruido). El hash usa un núcleo en otro proceso, y el loop solo se despierta cada ~35 ms para mandar el bloque siguiente. El hash tardó prácticamente lo mismo en los dos modos (4.7 s y 4.9 s): mover el trabajo de lugar no lo hace más rápido, pero libera al loop.

### M3 — Techo del pool

[`medir_techo.py`](mediciones/medir_techo.py) manda N `POST /tareas` simultáneos y mide cuántos entran, la latencia del POST, el tiempo total hasta vaciar todo, el throughput y cuánto esperó cada tarea en la cola. Hice cuatro barridos para separar los distintos límites.

**a) Configuración por defecto (`WORKERS=4`, `COLA_MAX=100`), tareas `esperar` de 1 s**

| N | Aceptadas | 503 | POST mediana | Total | Throughput | Espera en cola (mediana / máx) |
|--:|--:|--:|--:|--:|--:|--:|
| 1 | 1 | 0 | 3 ms | 1.02 s | 1.0 /s | 0.00 / 0.00 s |
| 10 | 10 | 0 | 12 ms | 3.11 s | 3.2 /s | 1.00 / 2.00 s |
| 50 | 50 | 0 | 26 ms | 13.07 s | 3.8 /s | 5.99 / 11.97 s |
| 100 | 100 | 0 | 73 ms | 25.14 s | 4.0 /s | 11.95 / 23.91 s |
| 200 | 104 | 96 | 147 ms | 26.15 s | 4.0 /s | 12.45 / 24.90 s |
| 500 | 104 | 396 | 381 ms | 26.17 s | 4.0 /s | 12.45 / 24.90 s |
| 1.000 | 108 | 892 | 914 ms | 27.25 s | 4.0 /s | 12.94 / 25.03 s |
| 10.000 | 196 | 9.804 | 16.729 ms | 52.12 s | 3.8 /s | 23.74 / 25.03 s |

**b) Cola sin tope práctico (`COLA_MAX=100000`), N = 1.000 tareas de 1 s, variando `WORKERS`**

| WORKERS | Total | Throughput | Espera en cola mediana | POST mediana |
|--:|--:|--:|--:|--:|
| 10 | 100.29 s | 10.0 /s | 48.84 s | 800 ms |
| 100 | 10.26 s | 97.5 /s | 3.88 s | 755 ms |
| 1.000 | 2.56 s | 391 /s | 0.00 s | 784 ms |

**c) Workers de sobra (`WORKERS=10000`): el techo del propio loop**

| N | Aceptadas | POST mediana | POST máx | Total | Throughput |
|--:|--:|--:|--:|--:|--:|
| 1.000 | 1.000 | 743 ms | 1.399 ms | 2.46 s | 406 /s |
| 5.000 | 5.000 | 5.663 ms | 11.743 ms | 12.83 s | 390 /s |
| 10.000 | 10.000 | 17.084 ms | 29.969 ms | 31.34 s | 319 /s |

**d) CPU-bound: 32 tareas `hashear` de 1 millón de iteraciones (`WORKERS=32`), variando `PROCESOS_CPU`**

| PROCESOS_CPU | Total | Throughput | Speedup contra 1 proceso |
|--:|--:|--:|--:|
| 1 | 10.44 s | 3.1 /s | 1.0x |
| 2 | 5.78 s | 5.5 /s | 1.8x |
| 4 | 3.01 s | 10.6 /s | 3.5x |
| 8 | 2.04 s | 15.7 /s | 5.1x |
| 16 | 1.48 s | 21.7 /s | 7.1x |

**Interpretación.** Hay tres techos distintos, y cuál manda depende del tipo de tarea y de la configuración:

1. **Para I/O, el primer techo es `WORKERS`** (tabla a). Cada worker procesa una tarea a la vez, así que con 4 workers y tareas de 1 s el throughput se clava en **4 tareas/s**, haya 10 o 100 en espera. El tiempo total crece lineal con N (25 s para 100), y lo que crece es la espera en la cola, no la ejecución. La tabla b lo confirma: el throughput sigue exactamente a `WORKERS` (10 → 10/s, 100 → 97.5/s). Como `esperar` no consume CPU, subir los workers es prácticamente gratis: cada worker es una corrutina de unos pocos KB y no un thread.
2. **Después viene `COLA_MAX`.** A partir de N ≈ 104 (100 en la cola más 4 que los workers sacaron enseguida), el resto recibe **503** y el total deja de crecer. El backpressure funciona como se esperaba: rechaza rápido en vez de acumular. Con 10.000 entran 196 y no 104, porque mientras el loop procesaba la avalancha de POSTs los workers fueron vaciando lugares en la cola.
3. **El techo final es el propio event loop atendiendo HTTP** (tablas b y c). Con 1.000 workers, 1.000 tareas de 1 s deberían tardar ~1 s, pero tardan 2.56 s: solo recibir los 1.000 POSTs le lleva al loop ~1.5 s (el POST máximo). Cada POST pasa por uvicorn, el parseo HTTP, la validación de Pydantic y la serialización JSON, todo en el único hilo, a unos **400 POSTs por segundo** en esta máquina. Con 10.000 cae a 319/s, porque cuantas más conexiones abiertas, más trabajo por vuelta del loop. Eso también explica la columna "POST mediana" de la tabla a: incluso los rechazos con 503 tardan cada vez más (16.7 s con 10.000), porque esperan su turno en el mismo hilo. Pasar este techo exige más de un proceso, y entonces el estado ya no puede vivir en un `dict` (ver Limitaciones).

Para CPU-bound (tabla d), el techo son **los núcleos**, y los workers no influyen. Duplicar procesos casi duplica el throughput hasta 4. Después la curva se aplana: 8 procesos dan 5.1x y 16 dan 7.1x, no 16x. El motivo es que el i5-14400 tiene 6 núcleos de rendimiento con hyper-threading y 4 de eficiencia. De los 16 "CPUs", solo 6 son núcleos rápidos completos: los hilos gemelos comparten las unidades del núcleo y los núcleos E son más lentos. Además, cada bloque de 100.000 iteraciones es una ida y vuelta con pickle entre procesos. Más procesos que núcleos no agregaría nada. El default de 2 procesos es conservador, para no quitarle toda la CPU a la máquina.

## 5. Conceptos del curso aplicados

- **Clase 6 (señales).** El apagado empieza con SIGTERM/SIGINT. `loop.add_signal_handler` no corre el handler en medio de cualquier instrucción, como `signal.signal`: por dentro usa el truco del self-pipe (`signal.set_wakeup_fd`). La señal escribe un byte en un socket que el loop vigila, y el handler corre como un callback más del loop, en un punto seguro. Por eso el handler puede tocar el estado del servidor (`_servidor.should_exit = True`) sin riesgo.
- **Clase 11 (sincronización: productor-consumidor y semáforos).** El pool es el mismo productor-consumidor de la clase 11: los endpoints producen ids en una cola compartida y los N workers los consumen. Acá no hace falta lock, porque el loop no interrumpe entre `await`s. El `asyncio.Semaphore` de las descargas es el mismo semáforo contador de la clase, limitando el acceso a un recurso finito (conexiones/descriptores), pero sin bloquear un thread: el que no consigue lugar hace `await` y cede el loop.
- **Clase 13-14 (sockets y servidores concurrentes).** El `servidor_lento` es un servidor TCP con `asyncio.start_server` que parsea a mano la primera línea del HTTP: la misma estructura que los servidores de la clase 14, pero atendiendo a cada cliente en una corrutina en lugar de un thread o un proceso.
- **Clase 17 (I/O multiplexing).** El event loop de asyncio es un bucle de `select`/`epoll` como el de `servidor_selectors.py`: registra sockets, espera a que alguno esté listo y llama al callback correspondiente. M2 es la demostración: mientras el hash corre en el loop, nadie vuelve al `epoll`, y los requests se acumulan en el socket sin que nadie los lea.
- **Clase 18 (de yield a asyncio).** Una corrutina es un generador mejorado: `await` es un punto de suspensión donde le devuelve el control al loop, igual que `yield`. De ahí sale la regla de que `time.sleep` es un bug: no tiene punto de suspensión y retiene el control. De ahí también sale que solo haya cambio de contexto en un `await`, que es la razón de no necesitar locks.
- **Clase 19 (HTTP y FastAPI).** Endpoints `async def`, validación con Pydantic (422 automático), códigos de estado HTTP con significado (201, 404, 409, 503), el `lifespan` para crear y cerrar los recursos compartidos, y uvicorn con un solo proceso porque el estado está en memoria.
- **Clase 20 (asyncio en red).** `asyncio.gather` para solapar las descargas (M1), `asyncio.timeout` para el timeout por tarea, la cancelación como `CancelledError` inyectado en el `await` pendiente, `cancelling()` para saber quién canceló, y la regla de relanzar el `CancelledError` propio.
- **Clase 21 (asyncio avanzado).** `asyncio.Queue` con `maxsize` como backpressure, el centinela `object()` para apagar a los workers, `run_in_executor` para sacar el CPU-bound del loop y la elección de `ProcessPoolExecutor` sobre threads por el GIL.
- **Clase 22 (`concurrent.futures`).** Un future que ya arrancó no se puede cancelar: de ahí sale el hash en bloques. La función que va al pool tiene que ser picklable, así que vive a nivel de módulo en `cpu.py`. El `initializer` prepara cada proceso hijo. Y está la guarda `if __name__ == '__main__'`, que evita el bucle de reimportación del método `spawn` en macOS y Windows.

## 6. Limitaciones conocidas

- **Un solo proceso, estado en memoria.** El techo de ~400 POSTs/s de M3 es el de un hilo. Escalar a varios procesos exigiría sacar el registro y la cola a algo compartido (por ejemplo Redis, o Celery), y eso está fuera de las restricciones del TP.
- **El registro nunca se purga.** Las tareas terminadas quedan para siempre: la memoria crece con el uso, y `GET /tareas` sin filtro cuesta más con cada tarea (164 ms de loop congelado con 10.000). Faltaría paginación en `GET /tareas` y una política de expiración de tareas viejas.
- **El estado no se restaura.** Al arrancar, el volcado previo solo se informa, que es lo que pide la consigna. Las tareas `pendiente` del volcado no se vuelven a encolar.
- **Un worker que muere no se reemplaza.** El `done_callback` lo loguea, pero no lanza uno nuevo. Hoy no hay ningún camino conocido para que pase, porque todo lo que ejecuta la tarea está bajo `except Exception`, pero si pasara el pool quedaría más chico hasta el reinicio.
- **Cancelar un `hashear` no es instantáneo.** Demora hasta un bloque (~35 ms con 100.000 iteraciones). Bloques más chicos cancelarían antes, pero con más overhead de ida y vuelta entre procesos.
- **El timeout de una descarga individual es fijo (30 s, en el cliente httpx).** No depende del `timeout` de la tarea. Si la tarea tiene un timeout menor, manda el de la tarea, pero no existe un timeout por URL configurable.
- **No hay autenticación ni límite por cliente.** Cualquiera puede llenar la cola. El 503 protege al servidor, pero no reparte la capacidad de forma justa entre clientes.
- **Si un proceso del pool de CPU muere, el pool queda roto.** Si el sistema mata a un hijo del `ProcessPoolExecutor` (por ejemplo el OOM killer), el executor queda marcado como roto y todas las tareas `hashear` siguientes fallan con `BrokenProcessPool` hasta reiniciar el servidor. Las demás tareas siguen andando. La solución sería capturar esa excepción y recrear el pool.
- **Los tiempos se miden con `time.time()`.** Si el reloj del sistema se ajusta en medio de una tarea (por NTP), su duración en `/estadisticas` sale corrida. Para duraciones, lo correcto sería `time.monotonic()`.

## 7. Lo que aprendí

Antes de este TP pensaba que concurrencia era sinónimo de threads. Termine aprendiendo (con muchas preguntas a claude xq no me cerraba) que un solo hilo puede atender cientos de clientes si nunca se queda esperando, y que el await es el único punto donde el loop puede cambiar de tarea.

Lo que más me costó fue la cancelación. Tuve que entender que cancel() no cortaba nada en el momento, que lanza un CancelledError en el await pendiente, y que un future de proceso ya iniciado no se puede cancelar, de ahí el hash en bloques. 

Me gusto mucho usar la IA como tutor: pedí planes para entender cada tema antes de escribir código y le pedia cada 5 lineas que me explicara cosas, y escribí los tests primero para que me mostraran dónde fallaba mi diseño, etc. La verdad muy lindo proyecto.