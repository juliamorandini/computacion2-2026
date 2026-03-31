import os
import argparse

def main():
    parser = argparse.ArgumentParser(description="Detector de enlaces simbólicos rotos")
    parser.add_argument("directorio", help="Directorio donde buscar")
    parser.add_argument("--delete", action="store_true", help="Ofrecer borrar los enlaces rotos")
    parser.add_argument("--quiet", action="store_true", help="Solo mostrar el conteo")
    
    args = parser.parse_args()
    
    enlaces_rotos = []

    if not args.quiet:
        print(f"Buscando enlaces simbólicos rotos en {args.directorio}...\n")

    for root, dirs, files in os.walk(args.directorio):
        # Chequear tanto archivos como directorios que puedan ser symlinks
        for nombre in files + dirs:
            ruta_completa = os.path.join(root, nombre)
            
            # islink evalúa el enlace en sí, exists evalúa el destino
            if os.path.islink(ruta_completa) and not os.path.exists(ruta_completa):
                destino = os.readlink(ruta_completa)
                enlaces_rotos.append((ruta_completa, destino))

    if args.quiet:
        print(len(enlaces_rotos))
        return

    if not enlaces_rotos:
        print("No se encontraron enlaces rotos.")
        return

    print("Enlaces rotos encontrados:")
    for ruta, destino in enlaces_rotos:
        print(f"  {ruta} -> {destino} (no existe)")
    print(f"\nTotal: {len(enlaces_rotos)} enlaces rotos\n")

    if args.delete:
        borrados = 0
        for ruta, destino in enlaces_rotos:
            respuesta = input(f"¿Borrar {ruta}? [s/N]: ")
            if respuesta.lower() == 's':
                try:
                    os.unlink(ruta)
                    print("  Borrado.")
                    borrados += 1
                except Exception as e:
                    print(f"  Error al borrar: {e}")
        print(f"\nSe borraron {borrados} enlaces.")

if __name__ == "__main__":
    main()
    