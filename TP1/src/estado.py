"""estado.py - Inicialización del snapshot global y recursos de sincronización.

Este módulo centraliza la creación del estado compartido entre todos los
componentes del monitor.  Usa `multiprocessing.Manager` para obtener un
diccionario que sobrevive al fork y es visible desde cualquier proceso.
"""

from multiprocessing import Manager, Lock, Value


def crear_estado():
    """
    Crea y retorna el snapshot global junto con su Lock de sincronización
    y una bandera verbose compartida.

    El snapshot es un ``Manager().dict()`` que vivirá en un proceso-servidor
    aparte.  Cada acceso (lectura o escritura) viaja por IPC (serialización
    pickle), por lo que es más lento que ``Value`` o ``Array``, pero permite
    almacenar estructuras arbitrarias (dicts anidados, listas, etc.).

    El ``Lock`` debe ser usado **solo** por el Agregador cuando actualiza
    múltiples claves relacionadas (p. ej. datos + timestamp), garantizando
    que el Display siempre vea un estado consistente.

    La bandera ``verbose_flag`` (``Value("b")``) permite activar/desactivar
    logs verbosos en TODOS los procesos (Recolector, Agregador, Analizadores)
    desde la señal SIGUSR2.

    Returns
    -------
    tuple
        ``(snapshot, lock, verbose_flag)`` donde:
        - ``snapshot`` (dict): Manager.dict con las vistas del monitor.
        - ``lock`` (Lock): multiprocessing.Lock para proteger escrituras
          compuestas.
        - ``verbose_flag`` (Value): multiprocessing.Value("b") booleano
          compartido para modo verbose global.
    """
    manager = Manager()

    snapshot = manager.dict()
    lock = Lock()
    verbose_flag = Value("b", False)  # False = silencioso en TUI, True = verbose

    # Inicializamos las claves conocidas para que el Display sepa
    # qué esperar desde el arranque.
    snapshot["resumen"] = {}
    snapshot["memoria"] = {}
    snapshot["fds"] = {}
    snapshot["threads"] = {}
    snapshot["senales"] = {}
    snapshot["scheduling"] = {}
    snapshot["sistema"] = {}
    snapshot["timestamps"] = manager.dict()

    return snapshot, lock, verbose_flag
