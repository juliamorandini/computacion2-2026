import argparse
import secrets
import string
import sys

def generar_password(longitud, usar_numeros, usar_simbolos):
    # Definimos los pools de caracteres
    letras = string.ascii_letters
    numeros = string.digits if usar_numeros else ""
    simbolos = "!@#$%&*" if usar_simbolos else ""
    
    pool = letras + numeros + simbolos
    
    if not pool:
        # Caso borde: si el usuario desactivara todo (aunque aquí las letras son fijas)
        return ""

    # Generamos la contraseña eligiendo caracteres aleatorios del pool
    return "".join(secrets.choice(pool) for _ in range(longitud))

def main():
    parser = argparse.ArgumentParser(
        description="Generador de contraseñas seguras para la terminal."
    )
    
    # Argumentos opcionales con valores por defecto
    parser.add_argument("-n", "--length", type=int, default=12,
                        help="Longitud de la contraseña (default: 12)")
    
    parser.add_argument("--no-symbols", action="store_true",
                        help="Excluir símbolos especiales (!@#$%&*)")
    
    parser.add_argument("--no-numbers", action="store_true",
                        help="Excluir números")
    
    parser.add_argument("--count", type=int, default=1,
                        help="Cuántas contraseñas generar (default: 1)")

    args = parser.parse_args()

    # Validaciones básicas
    if args.length < 1:
        print("Error: La longitud debe ser al menos 1.", file=sys.stderr)
        sys.exit(1)

    # Generación
    try:
        for _ in range(args.count):
            # Invertimos la lógica de los flags: si --no-symbols es True, usar_simbolos es False
            password = generar_password(
                args.length, 
                not args.no_numbers, 
                not args.no_symbols
            )
            print(password)
    except Exception as e:
        print(f"Error inesperado: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()


    