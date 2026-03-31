from flask import Flask
import redis
import os

app = Flask(__name__)
r = redis.Redis(host='redis', port=6379, decode_responses=True)

@app.route('/')
def index():
    valor = r.get('contador_global') or 0
    return f"<h1>Hola desde Docker!</h1><p>El worker ha contado: <b>{valor}</b> veces.</p>"

if __name__ == '__main__':
    # host='0.0.0.0' es vital para que sea accesible desde fuera del contenedor
    app.run(host='0.0.0.0', port=5000)