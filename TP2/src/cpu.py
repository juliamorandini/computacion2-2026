"""cpu.py - Funciones CPU-bound puras para el ProcessPoolExecutor.

Estas funciones viven a nivel de módulo (top-level) porque deben ser
picklables para ser enviadas al ProcessPoolExecutor (clase 22).
Si estuvieran dentro de otra función o fueran lambdas, pickle fallaría.

sha256_bloque() trabaja con bytes crudos para que la ejecución en bloques
produzca el mismo resultado que una sola corrida de N iteraciones.
"""

import hashlib
import signal


def sha256_bloque(datos: bytes, iteraciones: int) -> bytes:
    """Aplica SHA-256 de forma iterada sobre bytes crudos.

    Esta función es un "bloque" de trabajo: recibe bytes, hace N
    iteraciones de SHA-256 y devuelve bytes.  Al trabajar siempre con
    bytes (no hex), encadenar bloques da el mismo resultado que hacer
    todas las iteraciones de una vez.

    Args:
        datos: Bytes de entrada (texto codificado o hash previo).
        iteraciones: Cantidad de pasadas de SHA-256 en este bloque.

    Returns:
        Bytes del hash después de las N iteraciones.
    """
    h = datos
    for _ in range(iteraciones):
        h = hashlib.sha256(h).digest()
    return h


def ignorar_sigint() -> None:
    """Initializer del ProcessPoolExecutor: ignora SIGINT en los hijos.

    Sin esto, Ctrl+C llegaría a los procesos hijos además del padre,
    causando excepciones inesperadas.  Al ignorar SIGINT, solo el
    proceso principal maneja la señal y decide cuándo cerrar el pool.
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)
