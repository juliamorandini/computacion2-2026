# Monitor de Procesos y Threads — TP1 Computación II

> Universidad de Mendoza — 2026
> Sistema multiproceso de monitoreo de procesos Linux mediante lectura directa de `/proc`.

---

## 1. Descripción general

Este proyecto implementa un **monitor en tiempo real** al estilo de `top` o `htop` pero desarrollado en Python. Lee datos directamente desde el pseudosistema de archivos `/proc` de Linux, sin depender de librerías externas como `psutil`. Muestra múltiples vistas detalladas sobre procesos, threads, memoria, descriptores de archivo, señales, entre otros.

## 2. Diagrama de Arquitectura

```text
       ┌──────────────────────────────────────┐
       │           SNAPSHOT GLOBAL            │
       │      (Manager dict compartido)       │
       │  ┌─────────────────────────────────┐ │
       │  │ "resumen"   : {...}             │ │
       │  │ "memoria"   : {...}             │ │
       │  │ ...                             │ │
       │  └─────────────────────────────────┘ │
       └────────▲─────────────────────▲───────┘
                │ escriben            │ lee
   ┌────────────┼─────────┬──────────┴────────┐
   │            │         │                   │
┌──▼──────┐ ┌───▼─────┐ ┌─▼──────┐      ┌─────▼────┐
│Resumen  │ │Memoria  │ │Agregad.│      │ Display  │
│cada 2s  │ │cada 3s  │ │y cola  │      │ TUI      │
└─────────┘ └─────────┘ └────────┘      └──────────┘
```
El sistema se basa en un modelo productor-consumidor y se orquesta a través de la librería `multiprocessing`.
- **`main.py`**: Es el orquestador principal. Arranca los procesos, configura el manejador de señales y apaga todo limpiamente (shutdown).
- **Recolector**: Escanea periódicamente `/proc` para encontrar los PIDs activos y reportarlos al sistema.
- **Analizadores**: 7 procesos independientes que consumen los PIDs (Resumen, Memoria, File Descriptors, Threads, Señales, Scheduling, Sistema).
- **Agregador**: Recibe datos de los analizadores vía `Queue` y actualiza el estado global.
- **Estado (Snapshot)**: Un diccionario de `multiprocessing.Manager()` protegido por `Lock`.
- **Display (TUI)**: Interfaz gráfica en consola desarrollada con `rich`.

## 3. Decisiones de Diseño

- **Arquitectura Multiproceso vs Multithread**: Se utilizó `multiprocessing` porque en Python el Global Interpreter Lock (GIL) impide el paralelismo real de hilos (threads) para tareas CPU-bound. Al usar procesos separados, los analizadores corren realmente en paralelo en múltiples núcleos.
- **IPC (Colas y Manager)**: Usé un `Manager.dict()` para el estado global porque permite guardar estructuras anidadas (diccionarios dentro de diccionarios) más fácilmente que `Array` o `Value`. Y usé `Queue` para que los analizadores envíen las actualizaciones al Agregador, evitando que todos escriban al dict global a la vez, lo cual reduciría la contención de candados (`Lock`).
- **Manejo de Race Conditions**: El acceso al snapshot global desde el Display y el Agregador está protegido con un `Lock`. Así se evita que el renderizado de la interfaz lea datos incompletos mientras el Agregador los está escribiendo.
- **Intervalos Diferenciados**: Cada analizador tiene su propio `Value` en memoria compartida, lo que permite que el usuario cambie su ritmo de refresh dinámicamente desde el TUI sin frenar a los demás.

## 4. Conceptos del Curso Aplicados

- **Procesos y /proc (Clase 3)**: El código inspecciona continuamente `/proc/<pid>/stat`, `status` y `cmdline` para calcular el uso de CPU y el estado.
- **Memoria Virtual y mmap (Clases 3 y 7)**: La vista de memoria lee `/proc/<pid>/maps` para mostrar los distintos segmentos (stack, heap, shared) correspondientes al mapeo de memoria virtual del proceso en RAM. 
- **Pipes e IPC (Clases 5 y 8)**: La comunicación entre analizadores y el agregador utiliza internamente tuberías administradas a través de `multiprocessing.Queue`.
- **Señales POSIX y Self-Pipe Pattern (Clase 6)**: El manejador atrapa señales externas como `SIGUSR1` (para exportar el snapshot a JSON) o `SIGHUP` (para recargar el `config.json`). Todo esto está implementado de manera *async-signal-safe* usando el patrón *self-pipe* hacia la interfaz gráfica de modo que las interrupciones no corrompan el pintado de `rich`.
- **Multiprocesamiento y Sincronización (Clases 8, 9 y 11)**: Orquestación de procesos con `Process`, semáforos/candados de sincronización (`Lock`) para compartir el `dict` del `Manager`, y control de parada a través de `Event`.

## 5. Limitaciones Conocidas

- **Procesos efímeros**: Si un proceso arranca y termina en la misma ventana de tiempo entre dos refrescos del Recolector, es probable que no llegue a ser registrado por el monitor.
- **Privilegios en espacio de usuario**: Para ver información de FDs y procesos de otros usuarios (ajenos) se requieren privilegios elevados (`root`). Sin ellos, los archivos fallan en su lectura y se omiten para evitar crasheos.
- **Carga de CPU en modo Turbo**: Debido a que la lectura, apertura y cierre de cientos de archivos en `/proc` es intensivo en E/S y CPU, configurar intervalos muy rápidos (menores a 0.5s) puede generar demasiada carga en el propio sistema monitor.

## 6. Cómo correr y testear

Hay dos formas principales de ejecutar el proyecto: de manera local o con Docker.

### Opción A: Ejecución local paso a paso

Sigue estos pasos desde la raíz del proyecto.

1. **Entrá a la carpeta del trabajo**:
   ```bash
   cd TP1
   ```

2. **Creá un entorno virtual**:
   - En Linux/WSL:
     ```bash
     python3 -m venv .venv
     ```
   - En PowerShell:
     ```powershell
     python -m venv .venv
     ```

3. **Activá el entorno virtual**:
   - En Linux/WSL:
     ```bash
     source .venv/bin/activate
     ```
   - En PowerShell:
     ```powershell
     .\.venv\Scripts\Activate.ps1
     ```

4. **Instalá las dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Ejecutá el monitor**:
   ```bash
   python src/main.py
   ```
   o, si tu sistema usa `python3`:
   ```bash
   python3 src/main.py
   ```

> Nota: si querés ver información de procesos de otros usuarios, podés correrlo con privilegios elevados, por ejemplo: `sudo python3 src/main.py`.
python -m pytest -q tests/test_windows_fallback.py tests/test_display.py tests/test_display_interaction.py
### Opción B: Uso de Docker (recomendado)

El entorno oficial de desarrollo y prueba utiliza Docker, compartiendo el espacio de nombres (`pid: host`).

1. **Construir la imagen**:
   ```bash
   docker compose build
   ```
2. **Ejecutar el monitor de forma interactiva (TUI)**:
   ```bash
   docker compose run --rm monitor
   ```

### Probando las señales

Desde otra terminal, podés probar el manejo de señales enviándoselas al proceso principal del monitor (`kill -SIGNAL <pid>`):
- `kill -SIGUSR1 <pid>`: genera un archivo local con el volcado (dump) JSON del sistema en vivo.
- `kill -SIGUSR2 <pid>`: activa o desactiva el modo verbose.
- `kill -SIGHUP <pid>`: recarga los valores dinámicos desde el archivo de configuración.
