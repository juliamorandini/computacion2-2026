import unittest
import subprocess
import os
import tempfile

class TestBuscar(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Se ejecuta una vez antes de todos los tests."""
        cls.script_path = os.path.abspath("buscar.py")
        # Crear un archivo temporal para las pruebas
        cls.test_file = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8')
        cls.test_file.write(
            "Línea 1: Error de conexión\n"
            "Línea 2: Todo ok\n"
            "Línea 3: error de timeout\n"
            "Línea 4: ADVERTENCIA Crítica"
        )
        cls.test_file.close()

    @classmethod
    def tearDownClass(cls):
        """Se ejecuta una vez al finalizar todos los tests."""
        if os.path.exists(cls.test_file.name):
            os.remove(cls.test_file.name)

    def run_script(self, args):
        """Helper para ejecutar el script y capturar salida."""
        return subprocess.run(
            ["python3", self.script_path] + args,
            capture_output=True,
            text=True
        )

    def test_busqueda_exitosa(self):
        """Debe encontrar la palabra 'Error' en el archivo."""
        result = self.run_script(["Error", self.test_file.name])
        self.assertIn("Error de conexión", result.stdout)
        self.assertEqual(result.returncode, 0)

    def test_ignore_case(self):
        """Debe encontrar 'error' (minúscula) usando el flag -i."""
        # Buscamos 'ERROR' (mayúscula) en un archivo que tiene 'error' (minúscula)
        result = self.run_script(["ERROR", self.test_file.name, "-i"])
        self.assertIn("error de timeout", result.stdout)
        self.assertIn("Error de conexión", result.stdout)

    def test_invert_match(self):
        """Debe mostrar las líneas que NO contienen la palabra."""
        result = self.run_script(["Línea", self.test_file.name, "-v"])
        # Como todas las líneas tienen 'Línea', el resultado debería ser vacío
        self.assertEqual(result.stdout.strip(), "")

    def test_archivo_no_existe(self):
        """Debe fallar con un mensaje de error si el archivo no existe."""
        result = self.run_script(["patron", "archivo_que_no_existe.txt"])
        self.assertIn("Error: No se puede leer", result.stderr)
        self.assertNotEqual(result.returncode, 0)

    def test_pipe_stdin(self):
        """Prueba la entrada por tubería (pipe)."""
        input_data = "Hola mundo\nBuscame a mi\nAdiós"
        result = subprocess.run(
            ["python3", self.script_path, "Buscame"],
            input=input_data,
            capture_output=True,
            text=True
        )
        self.assertIn("Buscame a mi", result.stdout)
        self.assertNotIn("Hola mundo", result.stdout)

if __name__ == "__main__":
    unittest.main()