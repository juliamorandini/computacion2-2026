# Plan: Trabajo Práctico 1 — Monitor de Procesos y Threads

## Contexto

Construir un monitor de procesos y threads en tiempo real para Linux usando Python 3.11+ y `multiprocessing`, siguiendo el enfoque de tutoría activa del archivo `prompt.md`. No se permite `psutil`; se lee `/proc` directamente. El sistema corre dentro de Docker.

## Enfoque recomendado

Vamos a avanzar por fases, con el estilo de tutoría del prompt: primero preguntamos, luego escribimos, luego validamos.

### Fase 1: Bootstrap

- Crear la estructura de carpetas (`src/`, `tests/`).
- Crear `Dockerfile`, `docker-compose.yml` (con `pid: host` para ver los procesos del host), `requirements.txt` (incluir `rich`), `config.json`.
- Verificar que el contenedor levante y pueda leer `/proc`.

### Fase 2: Parser de `/proc` (`procfs.py`)

- Implementar funciones helper para leer y parsear:
  - `/proc/<pid>/stat`
  - `/proc/<pid>/status`
  - `/proc/<pid>/cmdline`
  - `/proc/<pid>/maps`
  - `/proc/<pid>/fd/`
  - `/proc/<pid>/task/`
- Esto es la base de todo; sin datos correctos acá, las vistas fallan.

### Fase 3: Estado compartido y Agregador

- Definir el snapshot global usando `multiprocessing.Manager().dict()`.
- Decidir dónde se usan `multiprocessing.Lock` para proteger la escritura concurrente.
- Implementar el proceso agregador que recibe datos de los analizadores y actualiza el snapshot.

### Fase 4: Recolector (`recolector.py`)

- Implementar el proceso que liste PIDs desde `/proc`.
- Definir cómo distribuye trabajo a los analizadores (vía `Queue`, lista de PIDs, etc.).

### Fase 5: Analizadores (`analizadores/`)

- Crear los 7 procesos analizadores, cada uno con su propio intervalo de refresco ajustable.
- Comenzar por `resumen.py` (más simple) y luego `memoria.py`, `sistema.py`, etc.
- Usar `multiprocessing.Value` para almacenar el intervalo actual y que el display pueda modificarlo.

### Fase 6: Interfaz de usuario (`display.py`)

- Usar la librería `rich` para la TUI (más sencilla que `curses`).
- Mostrar lista de procesos y panel de detalle inferior.
- Implementar navegación (`↑/↓`, `Enter` para pin, `/` filtrar, `u` filtrar user, `c` toggle orden, `+/-` ajustar intervalo, `q` salir).
- Cambiar de vista con teclas `1-7`.

### Fase 7: Manejo de señales (`senales.py`)

- Implementar handlers para:
  - `SIGINT` / `SIGTERM` (shutdown limpio)
  - `SIGHUP` (reload config)
  - `SIGUSR1` (dump a JSON)
  - `SIGUSR2` (toggle verbose)
  - `SIGWINCH` (repintar, opcional)
- Usar patrón **self-pipe** o `signal.set_wakeup_fd` para integrar señales con el loop principal.

### Fase 8: Integración y entrega

- `main.py` que arranque todo y gestione joins/terminación.
- `README.md` con arquitectura, decisiones de diseño, conceptos aplicados y cómo correrlo.
- Opcionalmente: tests, bonus.

## Verificación

- `docker compose up --build` levanta el monitorTUI.
- Navegación, filtrado, pinning funcionan.
- Señales (`kill -SIGUSR1 <pid>`, etc.) producen efecto observable.
- Las 7 vistas muestran datos correctos.
- Revisión de código para confirmar uso adecuado de `Lock` y ausencia de race conditions obvias.

## Notas

- Docker debe exponer el PID namespace del host (`pid: host`) o el monitor solo verá procesos del contenedor.
- Cada fase será tratada como una sesión de tutoría: preguntas previas, escritura conjunta y revisión de conceptos.
- El usuario solicita guardar este plan también en `TP1/PLAN.md` para referencia futura.
