import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "No se encontró la variable DATABASE_URL. Configúrala en el archivo .env "
        "con la cadena de conexión de tu base de datos en Neon."
    )


def obtener_conexion():
    """
    Crea y devuelve una nueva conexión a la base de datos PostgreSQL en Neon.
    Cada función de la API abre su propia conexión y la cierra al terminar.
    """
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def inicializar_base_datos():
    """
    Crea las tablas necesarias si no existen todavía.
    Se ejecuta una vez al arrancar la aplicación (evento startup en main.py).
    """
    ddl = """
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL
    );

    CREATE TABLE IF NOT EXISTS tipo_hurto (
        id_tipo SERIAL PRIMARY KEY,
        nombre VARCHAR(100) UNIQUE NOT NULL
    );

    CREATE TABLE IF NOT EXISTS hurto (
        id SERIAL PRIMARY KEY,
        id_tipo_hurto INTEGER NOT NULL REFERENCES tipo_hurto(id_tipo),
        denunciante VARCHAR(150) NOT NULL,
        direccion VARCHAR(255) NOT NULL,
        fecha_hurto DATE NOT NULL,
        fecha_registro TIMESTAMP NOT NULL DEFAULT NOW()
    );
    """
    with obtener_conexion() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()
