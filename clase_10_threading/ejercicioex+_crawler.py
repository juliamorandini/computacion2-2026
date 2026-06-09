#!/usr/bin/env python3
"""Crawler básico con un pool de hilos."""
import threading
import queue
import urllib.request
import re
import time

def crawler_worker(in_q):
    """Saca URLs de la cola y busca cuántos enlaces tienen dentro."""
    while True:
        url = in_q.get()
        if url is None:
            break
            
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            response = urllib.request.urlopen(req, timeout=5)
            html = response.read().decode('utf-8', errors='ignore')
            
            # Expresión regular simple para encontrar href="http..."
            links = re.findall(r'href=["\'](http[s]?://[^"\']+)', html)
            print(f"[✅ Éxito] {url} -> Encontró {len(links)} links")
            
        except Exception as e:
            print(f"[❌ Fallo] {url} -> Error: {e}")
            
        finally:
            in_q.task_done()

if __name__ == "__main__":
    URL_INICIAL = "https://es.wikipedia.org/wiki/Linux"
    NUM_WORKERS = 5

    print(f"Descargando {URL_INICIAL} para extraer links...")
    # Extraemos links iniciales secuencialmente para poblar la cola
    try:
        html_base = urllib.request.urlopen(URL_INICIAL).read().decode('utf-8')
        urls_encontradas = re.findall(r'href=["\'](http[s]?://[^"\']+)', html_base)
        # Tomamos solo las primeras 15 para no saturar
        urls_a_procesar = list(set(urls_encontradas))[:15] 
    except Exception as e:
        print("Fallo en URL inicial:", e)
        exit(1)

    print(f"Iniciando {NUM_WORKERS} workers para procesar {len(urls_a_procesar)} sub-links...\n")
    
    q = queue.Queue()
    
    hilos = []
    for _ in range(NUM_WORKERS):
        t = threading.Thread(target=crawler_worker, args=(q,))
        t.start()
        hilos.append(t)

    # Alimentamos la cola con los enlaces descubiertos
    inicio = time.time()
    for url in urls_a_procesar:
        q.put(url)

    # Bloqueamos el main hasta que la cola quede vacía (todas las task_done)
    q.join()

    # Frenamos los workers
    for _ in hilos:
        q.put(None)
    for t in hilos:
        t.join()

    print(f"\nCrawler finalizado en {time.time() - inicio:.2f} segundos.")