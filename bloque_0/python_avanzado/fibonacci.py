def fibonacci(limite=None):

    a, b = 0, 1
    while True:
        # Verificación de límite para la versión con tope
        if limite is not None and a > limite:
            break
            
        yield a
        
        a, b = b, a + b


if __name__ == "__main__":
    # CASO 1: Uso manual (Infinito)
    print("--- Uso con next() ---")
    fib = fibonacci()

    # Obtener los primeros 10
    for _ in range(10):
        print(next(fib), end=" ")  # 0 1 1 2 3 5 8 13 21 34
    
    print("\nContinuando la secuencia:")
    print(next(fib))  # 55
    print(next(fib))  # 89

    # CASO 2: Uso con límite
    print("\n--- Uso con límite (100) ---")
    for n in fibonacci(limite=100):
        print(n, end=" ")  # 0 1 1 2 3 5 8 13 21 34 55 89