import os
import argparse

def parsear_tamano(size_str):
    """Convierte un string como '1M' o '500K' a bytes."""
    size_str = size_str.upper().strip()
    multiplicadores = {'K': 1024, 'M': 1024**2, 'G': 1024**3}
    
    if size_str[-1] in multiplicadores:
        try:
            numero = float(size_str[:-1])
            return int(numero * multiplicadores[size_str[-1]])
        except ValueError:
            raise argparse.ArgumentTypeError(f"Formato de tamaño inválido: {size_str}")
    try:
        return int(size_str)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Formato de tamaño inválido: {size_str}")

def formatear_tamano(bytes_size):
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_size / (1024 * 1024 * 1024):.1f} GB"

def main():
    parser = argparse.ArgumentParser(description="Buscador de archivos grandes")
    parser.add_argument("directorio", help="Directorio donde buscar")
    parser.add_argument("--min-size", required=True, type=parsear_tamano, help="Tamaño mínimo (ej. 1M, 500K, 2G)")
    parser.add_argument("--type", choices=['f', 'd'], help="Filtrar por tipo (f = archivo, d = directorio)")
    parser.add_argument("--top", type=int, help="Mostrar solo los N más grandes")
    
    args = parser.parse_args()
    
    resultados = []
    total_bytes = 0

    # Recorrer el directorio de forma recursiva
    for root, dirs, files in os.walk(args.directorio):
        elementos = []
        if not args.type or args.type == 'f':
            elementos.extend([(f, 'f') for f in files])
        if not args.type or args.type == 'd':
            elementos.extend([(d, 'd') for d in dirs])

        for nombre, tipo in elementos:
            ruta_completa = os.path.join(root, nombre)
            try:
                # Usar lstat para evitar problemas con symlinks infinitos
                tamaño = os.lstat(ruta_completa).st_size
                if tamaño >= args.min_size:
                    resultados.append({'ruta': ruta_completa, 'tamaño': tamaño, 'tipo': tipo})
            except (FileNotFoundError, PermissionError):
                continue

    # Ordenar por tamaño de mayor a menor
    resultados.sort(key=lambda x: x['tamaño'], reverse=True)

    if args.top:
        print(f"Los {args.top} archivos más grandes:")
        for i, res in enumerate(resultados[:args.top], 1):
            print(f"  {i}. {res['ruta']} ({formatear_tamano(res['tamaño'])})")
    else:
        for res in resultados:
            print(f"{res['ruta']} ({formatear_tamano(res['tamaño'])})")
            total_bytes += res['tamaño']
        
        print(f"Total: {len(resultados)} archivos, {formatear_tamano(total_bytes)}")

if __name__ == "__main__":
    main()