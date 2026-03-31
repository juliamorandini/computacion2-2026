import argparse
import sys

def convertir():
    parser = argparse.ArgumentParser(description="Convierte temperaturas entre Celsius y Fahrenheit.")
    
    # Argumento posicional (número)
    parser.add_argument("valor", type=float, help="Temperatura a convertir")
    
    # Opción obligatoria con choices
    parser.add_argument("-t", "--to", required=True, 
                        choices=["celsius", "fahrenheit"], 
                        help="Unidad de destino")

    args = parser.parse_args()

    if args.to == "fahrenheit":
        resultado = (args.valor * 9/5) + 32
        print(f"{args.valor}°C = {resultado:.1f}°F")
    else:
        resultado = (args.valor - 32) * 5/9
        print(f"{args.valor}°F = {resultado:.2f}°C")

if __name__ == "__main__":
    convertir()
    