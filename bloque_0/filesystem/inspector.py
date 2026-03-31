import os
import stat
import argparse
from datetime import datetime

# Intentar importar pwd y grp (solo disponibles en sistemas Unix-like)
try:
    import pwd
    import grp
    UNIX_SYSTEM = True
except ImportError:
    UNIX_SYSTEM = False

def obtener_tipo_archivo(modo):
    if stat.S_ISDIR(modo): return "directorio"
    elif stat.S_ISLNK(modo): return "enlace simbólico"
    elif stat.S_ISREG(modo): return "archivo regular"
    elif stat.S_ISCHR(modo): return "dispositivo de caracteres"
    elif stat.S_ISBLK(modo): return "dispositivo de bloques"
    elif stat.S_ISFIFO(modo): return "FIFO/pipe"
    elif stat.S_ISSOCK(modo): return "socket"
    return "desconocido"

def formatear_tamano(bytes_size):
    if bytes_size < 1024:
        return f"{bytes_size} bytes"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size} bytes ({bytes_size / 1024:.2f} KB)"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size} bytes ({bytes_size / (1024 * 1024):.2f} MB)"
    else:
        return f"{bytes_size} bytes ({bytes_size / (1024 * 1024 * 1024):.2f} GB)"

def formatear_fecha(timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def main():
    parser = argparse.ArgumentParser(description="Inspector de archivos detallado")
    parser.add_argument("ruta", help="Ruta del archivo a inspeccionar")
    args = parser.parse_args()

    ruta = args.ruta

    try:
        # Usamos lstat para no seguir los symlinks automáticamente y poder inspeccionarlos
        st = os.lstat(ruta)
        tipo = obtener_tipo_archivo(st.st_mode)
        
        print(f"Archivo: {ruta}")
        
        # Manejo especial para symlinks
        if tipo == "enlace simbólico":
            destino = os.readlink(ruta)
            print(f"Tipo: {tipo} -> {destino}")
        else:
            print(f"Tipo: {tipo}")
            
        print(f"Tamaño: {formatear_tamano(st.st_size)}")
        
        # Permisos
        permisos_str = stat.filemode(st.st_mode)
        permisos_octal = oct(stat.S_IMODE(st.st_mode))[2:]
        print(f"Permisos: {permisos_str} ({permisos_octal})")
        
        # Propietario y Grupo
        if UNIX_SYSTEM:
            usuario = pwd.getpwuid(st.st_uid).pw_name
            grupo = grp.getgrgid(st.st_gid).gr_name
            print(f"Propietario: {usuario} (uid: {st.st_uid})")
            print(f"Grupo: {grupo} (gid: {st.st_gid})")
        else:
            print(f"Propietario (uid): {st.st_uid}")
            print(f"Grupo (gid): {st.st_gid}")
            
        print(f"Inodo: {st.st_ino}")
        print(f"Enlaces duros: {st.st_nlink}")
        
        # Fechas (st_birthtime no está disponible en todos los sistemas de archivos de Linux)
        try:
            print(f"Creación: {formatear_fecha(st.st_birthtime)}")
        except AttributeError:
            # Fallback a ctime (change time) en sistemas donde birthtime no existe
            print(f"Creación/Cambio de metadatos: {formatear_fecha(st.st_ctime)}")
            
        print(f"Última modificación: {formatear_fecha(st.st_mtime)}")
        print(f"Último acceso: {formatear_fecha(st.st_atime)}")

        # Contenido extra para directorios
        if tipo == "directorio":
            elementos = len(os.listdir(ruta))
            print(f"Contenido: {elementos} elementos")

    except FileNotFoundError:
        print(f"Error: El archivo o directorio '{ruta}' no existe.")
    except PermissionError:
        print(f"Error: No tienes permisos para inspeccionar '{ruta}'.")

if __name__ == "__main__":
    main()