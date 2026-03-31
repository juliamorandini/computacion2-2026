import argparse
import json
import sys

def obtener_valor(datos, ruta):
    claves = ruta.split('.')
    actual = datos
    try:
        for clave in claves:
            if isinstance(actual, list):
                actual = actual[int(clave)]
            else:
                actual = actual[clave]
        return actual
    except (KeyError, IndexError, ValueError, TypeError):
        return None

def establecer_valor(datos, ruta, valor):
    claves = ruta.split('.')
    actual = datos
    for clave in claves[:-1]:
        if isinstance(actual, list):
            actual = actual[int(clave)]
        else:
            actual = actual[clave]
    
    # Intentar convertir booleanos o números si es posible
    if valor.lower() == 'true': valor = True
    elif valor.lower() == 'false': valor = False
    elif valor.isdigit(): valor = int(valor)
    
    if isinstance(actual, list):
        actual[int(claves[-1])] = valor
    else:
        actual[claves[-1]] = valor

def main():
    parser = argparse.ArgumentParser(description="Procesador de JSON")
    parser.add_argument("archivo", help="Archivo JSON o '-' para stdin")
    parser.add_argument("--keys", action="store_true", help="Listar claves del primer nivel")
    parser.add_argument("--get", metavar="KEY", help="Obtener valor usando notación con puntos")
    parser.add_argument("--pretty", action="store_true", help="Formatear con indentación")
    parser.add_argument("--set", nargs=2, metavar=("KEY", "VALUE"), help="Modificar un valor")
    parser.add_argument("-o", "--output", help="Archivo de salida (default: stdout)")

    args = parser.parse_args()

    # Cargar JSON
    try:
        if args.archivo == '-':
            datos = json.load(sys.stdin)
        else:
            with open(args.archivo, 'r', encoding='utf-8') as f:
                datos = json.load(f)
    except Exception as e:
        print(f"Error al leer JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # Procesar comandos
    if args.keys:
        if isinstance(datos, dict):
            for key in datos.keys():
                print(key)
        else:
            print("El elemento raíz no es un objeto/diccionario.")
            
    elif args.get:
        valor = obtener_valor(datos, args.get)
        if valor is not None:
            if isinstance(valor, (dict, list)):
                print(json.dumps(valor, indent=4 if args.pretty else None))
            else:
                print(valor)
        else:
            print("Clave no encontrada.", file=sys.stderr)
            
    elif args.set:
        establecer_valor(datos, args.set[0], args.set[1])
        salida = json.dumps(datos, indent=4 if args.pretty else None)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(salida)
            print(f"Guardado en {args.output}")
        else:
            print(salida)
            
    elif args.pretty:
        print(json.dumps(datos, indent=4))

if __name__ == "__main__":
    main()