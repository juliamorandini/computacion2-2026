import argparse
import sys
import re

def procesar_lineas(lineas, patron, args, nombre_archivo, multiples_archivos):
    flags = re.IGNORECASE if args.ignore_case else 0
    coincidencias = 0

    for num_linea, linea in enumerate(lineas, 1):
        linea = linea.rstrip('\n')
        # Verificar coincidencia
        coincide = bool(re.search(patron, linea, flags))
        
        # Invertir resultado si -v está activado
        if args.invert:
            coincide = not coincide

        if coincide:
            coincidencias += 1
            if not args.count:
                prefijo = ""
                if multiples_archivos:
                    prefijo += f"{nombre_archivo}:"
                if args.line_number or multiples_archivos:
                    prefijo += f"{num_linea}: "
                
                print(f"{prefijo}{linea}")
    
    if args.count:
        if multiples_archivos:
            print(f"{nombre_archivo}: {coincidencias} coincidencias")
        else:
            print(f"{coincidencias} coincidencias")
    
    return coincidencias

def main():
    parser = argparse.ArgumentParser(description="Mini-grep en Python")
    parser.add_argument("patron", help="El patrón a buscar")
    parser.add_argument("archivos", nargs="*", help="Archivos a procesar")
    parser.add_argument("-i", "--ignore-case", action="store_true", help="Búsqueda insensible a mayúsculas")
    parser.add_argument("-n", "--line-number", action="store_true", help="Mostrar número de línea")
    parser.add_argument("-c", "--count", action="store_true", help="Solo mostrar conteo de coincidencias")
    parser.add_argument("-v", "--invert", action="store_true", help="Mostrar líneas que NO coinciden")

    args = parser.parse_args()
    total_coincidencias = 0
    multiples_archivos = len(args.archivos) > 1

    # Leer de stdin si no hay archivos
    if not args.archivos:
        if not sys.stdin.isatty():
            total_coincidencias += procesar_lineas(sys.stdin, args.patron, args, "stdin", False)
        else:
            print("Error: Proporciona un archivo o usa un pipe (|) para enviar datos.", file=sys.stderr)
            sys.exit(1)
    else:
        for archivo in args.archivos:
            try:
                with open(archivo, 'r', encoding='utf-8') as f:
                    total_coincidencias += procesar_lineas(f, args.patron, args, archivo, multiples_archivos)
            except FileNotFoundError:
                print(f"buscar.py: {archivo}: No existe el archivo", file=sys.stderr)

    if args.count and multiples_archivos:
        print(f"Total: {total_coincidencias} coincidencias")

if __name__ == "__main__":
    main()