#!/usr/bin/env python3
"""Map-Reduce para conteo de palabras."""
from multiprocessing import Pool
from functools import reduce

TEXTOS = [
    "el rapido zorro marron salta sobre el perro perezoso",
    "el perro duerme bajo el arbol mientras el zorro corre",
    "rapido como el viento el zorro vuelve a saltar sobre el perro",
    "el arbol es viejo y el perro lo mira con curiosidad",
    "saltar correr el zorro y el perro juegan bajo el arbol",
]

def mapper(texto):
    conteo = {}
    for palabra in texto.lower().split():
        conteo[palabra] = conteo.get(palabra, 0) + 1
    return conteo

def reducer(dict1, dict2):
    resultado = dict1.copy()
    for palabra, count in dict2.items():
        resultado[palabra] = resultado.get(palabra, 0) + count
    return resultado

if __name__ == "__main__":
    with Pool(4) as pool:
        conteos_parciales = pool.map(mapper, TEXTOS)

    conteo_total = reduce(reducer, conteos_parciales)
    palabras_ordenadas = sorted(conteo_total.items(), key=lambda x: -x[1])

    print("Top palabras más frecuentes:")
    for palabra, count in palabras_ordenadas[:10]:
        print(f"  {palabra:15s} {count}")