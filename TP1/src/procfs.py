# procfs.py - Helpers para leer /proc
"""
Módulo con funciones helper para leer y parsear archivos de /proc.

Diseño:
- Todas las funciones públicas retornan dicts simples.
- Errores esperados (FileNotFoundError, PermissionError, ProcessLookupError)
  se atrapan y retornan None para que el llamador lo ignore.
- Otros errores (parsing, etc.) suben y deben ser tratados por el llamador.
- Caching de UID → usuario en memoria (per-proceso, no compartido).
"""

import os
import pwd

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

SIGNUM_A_NOMBRE = {
    1: "SIGHUP",
    2: "SIGINT",
    3: "SIGQUIT",
    4: "SIGILL",
    5: "SIGTRAP",
    6: "SIGABRT",
    7: "SIGBUS",
    8: "SIGFPE",
    9: "SIGKILL",
    10: "SIGUSR1",
    11: "SIGSEGV",
    12: "SIGUSR2",
    13: "SIGPIPE",
    14: "SIGALRM",
    15: "SIGTERM",
    16: "SIGSTKFLT",
    17: "SIGCHLD",
    18: "SIGCONT",
    19: "SIGSTOP",
    20: "SIGTSTP",
    21: "SIGTTIN",
    22: "SIGTTOU",
    23: "SIGURG",
    24: "SIGXCPU",
    25: "SIGXFSZ",
    26: "SIGVTALRM",
    27: "SIGPROF",
    28: "SIGWINCH",
    29: "SIGIO",
    30: "SIGPWR",
    31: "SIGSYS",
}

# Cache de UID → nombre de usuario (per-proceso, no compartido entre procesos)
# Esto está bien porque /etc/passwd no cambia durante la ejecución del TP.
_UID_CACHE: dict[int, str] = {}


# ---------------------------------------------------------------------------
# Erroes esperados que retornan None (proceso no existe / sin permisos)
# ---------------------------------------------------------------------------

_ERRORES_ESPERADOS = (FileNotFoundError, PermissionError, ProcessLookupError)


def _leer_archivo(path: str) -> str | None:
    """
    Lee un archivo de /proc. Retorna su contenido o None si no se puede leer.
    Solo atrapa errores esperados (proceso no existe, sin permisos).
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except _ERRORES_ESPERADOS:
        return None


def _leer_entero(path: str) -> int | None:
    """
    Lee un archivo de /proc que contiene un solo entero.
    Retorna el entero o None si no se puede leer.
    """
    contenido = _leer_archivo(path)
    if contenido is None:
        return None
    try:
        return int(contenido.strip())
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Cache UID → usuario
# ---------------------------------------------------------------------------

def uid_a_usuario(uid: int) -> str:
    """
    Convierte un UID a nombre de usuario, con cache en memoria.
    """
    if uid not in _UID_CACHE:
        try:
            _UID_CACHE[uid] = pwd.getpwuid(uid).pw_name
        except KeyError:
            _UID_CACHE[uid] = str(uid)
    return _UID_CACHE[uid]


# ---------------------------------------------------------------------------
# Parseo de señales (hex → lista de nombres)
# ---------------------------------------------------------------------------

def _parsear_signal_hex(hex_str: str) -> list[str]:
    """
    Convierte un string con hex de bits de señales a lista de nombres.
    El string puede traer espacios (ej: "0000000000001000  ").
    """
    try:
        val = int(hex_str.strip(), 16)
    except ValueError:
        return []
    return [
        SIGNUM_A_NOMBRE[i]
        for i in range(1, 32)
        if val & (1 << (i - 1))  # bit 0 → señal 1, etc.
        if i in SIGNUM_A_NOMBRE
    ]


# ---------------------------------------------------------------------------
# Leer /proc/<pid>/stat
# ---------------------------------------------------------------------------

def _parsear_stat(contenido: str) -> dict:
    """
    Parsea el contenido de /proc/<pid>/stat.

    El campo comm está entre paréntesis y puede tener espacios.
    Usamos: primer '(' y último ')' para separar comm del resto.

    Retorna dict con los campos más importantes.
    """
    content = contenido.strip()
    primer_paren = content.find("(")
    ultimo_paren = content.rfind(")")

    if primer_paren == -1 or ultimo_paren == -1:
        raise ValueError("Formato inválido en /proc/<pid>/stat: no se encontraron paréntesis")

    # Parte antes del primer '(': el PID
    pid_str = content[:primer_paren].strip()
    pid = int(pid_str)

    # Entre paréntesis: comm (nombre del proceso, puede tener espacios)
    comm = content[primer_paren + 1 : ultimo_paren]

    # Todo lo que sigue después del último ')': el resto de los campos separados por espacio
    resto = content[ultimo_paren + 1 :].split()

    # resto tiene (en formato típico de /proc/<pid>/stat):
    # 0:state, 1:ppid, 2:pgrp, 3:session, 4:t້tty_nr, 5:tpgid, 6:flags,
    # 7:minflt, 8:cminflt, 9:majflt, 10:cmajflt, 11:utime, 12:stime,
    # 13:cutime, 14:cstime, 15:priority, 16:nice, 17:num_threads,
    # 18:itrealvalue, 19:starttime, 20:vsize, 21:rss, 22:rsslim,
    # 23:... etc.

    return {
        "pid": pid,
        "comm": comm,
        "state": resto[0] if len(resto) > 0 else "",
        "ppid": int(resto[1]) if len(resto) > 1 else None,
        "pgrp": int(resto[2]) if len(resto) > 2 else None,
        "session": int(resto[3]) if len(resto) > 3 else None,
        "tty_nr": int(resto[4]) if len(resto) > 4 else None,
        "tpgid": int(resto[5]) if len(resto) > 5 else None,
        "flags": int(resto[6]) if len(resto) > 6 else None,
        "minflt": int(resto[7]) if len(resto) > 7 else None,
        "cminflt": int(resto[8]) if len(resto) > 8 else None,
        "majflt": int(resto[9]) if len(resto) > 9 else None,
        "cmajflt": int(resto[10]) if len(resto) > 10 else None,
        "utime": int(resto[11]) if len(resto) > 11 else None,
        "stime": int(resto[12]) if len(resto) > 12 else None,
        "cutime": int(resto[13]) if len(resto) > 13 else None,
        "cstime": int(resto[14]) if len(resto) > 14 else None,
        "priority": int(resto[15]) if len(resto) > 15 else None,
        "nice": int(resto[16]) if len(resto) > 16 else None,
        "num_threads": int(resto[17]) if len(resto) > 17 else None,
        "itrealvalue": int(resto[18]) if len(resto) > 18 else None,
        "starttime": int(resto[19]) if len(resto) > 19 else None,
        "vsize": int(resto[20]) if len(resto) > 20 else None,
        "rss": int(resto[21]) if len(resto) > 21 else None,
        "rsslim": int(resto[22]) if len(resto) > 22 else None,
        # Campos de scheduling (índices 39 y 40 en resto = campos 40 y 41 en stat)
        "rt_priority": int(resto[39]) if len(resto) > 39 else None,
        "policy": int(resto[40]) if len(resto) > 40 else None,
    }


# Nota: parsear stat en tiempo de usuario exacto requiere conocer clock ticks (sysconf).
# La función de abajo (cpu_percent) es un placeholder para calcular %CPU en el consumidor.

def leer_stat(pid: int) -> dict | None:
    """
    Lee y parsea /proc/<pid>/stat.
    Retorna dict con campos parseados, o None si no se puede leer.
    """
    contenido = _leer_archivo(f"/proc/{pid}/stat")
    if contenido is None:
        return None
    return _parsear_stat(contenido)


# ---------------------------------------------------------------------------
# Leer /proc/<pid>/status
# ---------------------------------------------------------------------------

def _parsear_status(contenido: str) -> dict:
    """
    Parsea el contenido de /proc/<pid>/status.
    Retorna dict con pares key: value.
    Para campos de señales (hex), devuelve lista de nombres.
    Para campos en kB (VmSize, VmRSS, etc.), extrae el entero.
    """
    resultado: dict = {}
    for linea in contenido.splitlines():
        if ":" not in linea:
            continue
        key, value = linea.split(":", maxsplit=1)
        key = key.strip()
        value = value.strip()

        # Campos hex de señales
        if key in ("SigPnd", "ShdPnd", "SigBlk", "SigIgn", "SigCgt"):
            resultado[key] = _parsear_signal_hex(value)
        # Campos numéricos simples
        elif value.isdigit():
            resultado[key] = int(value)
        # Campos con unidades (ej: "123456 kB")
        elif value.endswith(" kB"):
            try:
                resultado[key] = int(value[:-3].strip())
            except ValueError:
                resultado[key] = value
        else:
            resultado[key] = value

    return resultado


def leer_status(pid: int) -> dict | None:
    """
    Lee y parsea /proc/<pid>/status.
    Retorna dict con los campos parseados, o None si no se puede leer.
    """
    contenido = _leer_archivo(f"/proc/{pid}/status")
    if contenido is None:
        return None
    return _parsear_status(contenido)


# ---------------------------------------------------------------------------
# Leer /proc/<pid>/cmdline
# ---------------------------------------------------------------------------

def leer_cmdline(pid: int) -> str | None:
    """
    Lee /proc/<pid>/cmdline y retorna la línea de comando como string.
    Reemplaza los null bytes con espacios.
    """
    contenido = _leer_archivo(f"/proc/{pid}/cmdline")
    if contenido is None:
        return None
    return contenido.replace("\x00", " ").strip()


# ---------------------------------------------------------------------------
# Leer /proc/<pid>/maps
# ---------------------------------------------------------------------------

def _clasificar_region(pathname: str, perms: str) -> str:
    """
    Clasifica una región de memoria en /proc/<pid>/maps.
    """
    if pathname == "[heap]":
        return "heap"
    if pathname == "[stack]":
        return "stack"
    if pathname == "[vvar]":
        return "vvar"
    if pathname == "[vdso]":
        return "vdso"
    if not pathname or pathname.startswith("["):
        return "anon"
    if ".so" in pathname:
        return "text" if "x" in perms else "data"
    # Ejecutable principal u otro archivo mapeado
    return "text" if "x" in perms else "data"


def _parsear_maps(contenido: str) -> dict:
    """
    Parsea /proc/<pid>/maps y retorna un dict con totales por categoría.
    Las categorías son: text, data, heap, stack, shared, anon, vvar, vdso.

    También guarda un resumen por módulo (pathname) si tiene nombre de archivo.
    """
    categorias = {
        "text": 0,
        "data": 0,
        "heap": 0,
        "stack": 0,
        "shared": 0,
        "anon": 0,
        "vvar": 0,
        "vdso": 0,
    }
    modulos: dict[str, int] = {}

    for linea in contenido.splitlines():
        if not linea.strip():
            continue
        partes = linea.split(maxsplit=5)
        if len(partes) < 4:
            continue

        # Columnas: address perms offset dev inode [pathname]
        direccion = partes[0]
        perms = partes[1]
        offset = partes[2]
        dev = partes[3]
        pathname = partes[5] if len(partes) > 5 else ""  # puede faltar

        # Calcular tamaño de la región
        addr_range = direccion.split("-")
        if len(addr_range) != 2:
            continue
        try:
            inicio = int(addr_range[0], 16)
            fin = int(addr_range[1], 16)
            size_kb = (fin - inicio) // 1024
        except ValueError:
            continue

        categoria = _clasificar_region(pathname, perms)

        if categoria in categorias:
            categorias[categoria] += size_kb
        else:
            categorias.setdefault("other", 0)
            categorias["other"] += size_kb

        # Trackear módulos individuales (solo si tienen nombre real de archivo)
        if pathname and not pathname.startswith("["):
            modulos[pathname] = modulos.get(pathname, 0) + size_kb

    resultado = {
        "totales_kb": categorias,
        "modulos": modulos,
    }
    return resultado


def leer_maps(pid: int) -> dict | None:
    """
    Lee y parsea /proc/<pid>/maps.
    Retorna dict con totales por categoría y módulos, o None si no se puede leer.
    """
    contenido = _leer_archivo(f"/proc/{pid}/maps")
    if contenido is None:
        return None
    return _parsear_maps(contenido)


# ---------------------------------------------------------------------------
# Leer /proc/<pid>/fd/ (file descriptors)
# ---------------------------------------------------------------------------

def _readlink_safe(link_path: str) -> str | None:
    """
    Lee el destino de un symlink (como /proc/<pid>/fd/<n>).
    Retorna el path target o None si falla.
    """
    try:
        return os.readlink(link_path)
    except _ERRORES_ESPERADOS:
        return None


def leer_fds(pid: int) -> list[dict] | None:
    """
    Lista los file descriptors abiertos de un proceso.
    Retorna lista de dicts con: fd, target, type.
    Retorna None si no se puede leer la carpeta /proc/<pid>/fd/.
    """
    fd_dir = f"/proc/{pid}/fd"
    try:
        entradas = os.listdir(fd_dir)
    except _ERRORES_ESPERADOS:
        return None

    fds = []
    for fd_str in entradas:
        # Ignorar cosas que no sean números enteros (no debería haber)
        try:
            fd = int(fd_str)
        except ValueError:
            continue
        target = _readlink_safe(os.path.join(fd_dir, fd_str))
        if target is None:
            continue

        # Clasificación simple por el target
        tipo = "other"
        if target.startswith("pipe:"):
            tipo = "pipe"
        elif target.startswith("socket:"):
            tipo = "socket"
        elif target.startswith("anon_inode:"):
            tipo = "anon"
        elif target.startswith("/"):
            tipo = "file"
        elif target in ("/dev/null", "/dev/zero", "/dev/urandom", "/dev/pts/") or "/dev/" in target:
            tipo = "dev"
        fds.append({"fd": fd, "target": target, "type": tipo})

    return fds


# ---------------------------------------------------------------------------
# Leer /proc/<pid>/task (threads)
# ---------------------------------------------------------------------------

def leer_task(pid: int) -> list[int] | None:
    """
    Lista los TIDs (threads) de un proceso.
    Retorna lista de enteros o None si no se puede leer.
    """
    path = f"/proc/{pid}/task"
    try:
        entradas = os.listdir(path)
    except _ERRORES_ESPERADOS:
        return None

    tids = []
    for entrada in entradas:
        try:
            tids.append(int(entrada))
        except ValueError:
            pass
    return tids


def leer_task_status(pid: int, tid: int) -> dict | None:
    """
    Lee y parsea /proc/<pid>/task/<tid>/status (status de un thread específico).
    Retorna dict con los campos parseados, o None si no se puede leer.
    """
    contenido = _leer_archivo(f"/proc/{pid}/task/{tid}/status")
    if contenido is None:
        return None
    return _parsear_status(contenido)
