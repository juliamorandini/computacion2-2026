import sys

def saludar():
    # sys.argv[0] es el nombre del script
    argumentos = sys.argv[1:]
    
    if not argumentos:
        print(f"Uso: {sys.argv[0]} <nombre>")
        sys.exit(1)
    
    # Unimos todos los argumentos por si el nombre tiene espacios
    nombre = " ".join(argumentos)
    print(f"Hola, {nombre}!")

if __name__ == "__main__":
    saludar()
