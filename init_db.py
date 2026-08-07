import psycopg2
import sys
import hashlib
import os

DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
DB_PORT = int(os.environ.get("DB_PORT", 5432))
DB_NAME = os.environ.get("DB_NAME", "DESA")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")

def get_connection(password=None):
    if password is None:
        password = DB_PASSWORD
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=password,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        print(f"Error al conectar a DB: {e}")
        return None

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    phone VARCHAR(30),
    birthdate DATE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'paciente',
    is_verified BOOLEAN DEFAULT FALSE,
    verification_token VARCHAR(10),
    verification_method VARCHAR(20) DEFAULT 'email',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    price NUMERIC(10,2) NOT NULL,
    duration_minutes INT DEFAULT 30
);

ALTER TABLE services ADD COLUMN IF NOT EXISTS duration_minutes INT DEFAULT 30;

CREATE TABLE IF NOT EXISTS appointments (
    id SERIAL PRIMARY KEY,
    patient_id INT REFERENCES users(id) ON DELETE SET NULL,
    patient_name VARCHAR(100) NOT NULL,
    patient_phone VARCHAR(30),
    patient_email VARCHAR(150),
    service_id INT REFERENCES services(id),
    service_name VARCHAR(150) NOT NULL,
    price NUMERIC(10,2) NOT NULL,
    appointment_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    status VARCHAR(20) DEFAULT 'confirmada',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS schedule_blocks (
    id SERIAL PRIMARY KEY,
    block_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    reason TEXT DEFAULT 'Bloqueado por la clínica',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

DEFAULT_SERVICES = [
    ("Consulta", "Consulta médica especializada ginecológica y obstetricia con revisión integral.", 190.00, 30),
    ("Papanicolaou", "Examen de Papanicolaou (Citología cérvico-vaginal) para prevención y diagnóstico.", 130.00, 30),
    ("Ultrasonido", "Ultrasonido pélvico / obstétrico / ginecológico de alta definición.", 200.00, 30),
    ("Consulta + Ultrasonido", "Evaluación médica completa combinada con examen de ultrasonido.", 390.00, 30),
    ("Consulta + Ultrasonido + Papanicolaou", "Chequeo ginecológico integral completo.", 430.00, 60),
]

def init_database(db_password=None):
    print(f"Intentando conectar a la base de datos PostgreSQL '{DB_NAME}'...")
    conn = get_connection(db_password)
    if not conn:
        print("Aviso: No se pudo conectar a PostgreSQL local directamente.")
        return False

    cursor = conn.cursor()
    try:
        print("Actualizando tablas en la base de datos DESA...")
        cursor.execute(SCHEMA_SQL)

        # Actualizar duración y descripción del servicio completo
        cursor.execute("UPDATE services SET duration_minutes = 60, description = 'Chequeo ginecológico integral completo.' WHERE name ILIKE '%Papanicolaou%' AND name ILIKE '%Ultrasonido%';")
        
        cursor.execute("SELECT COUNT(*) FROM services;")
        count = cursor.fetchone()[0]
        if count == 0:
            print("Poblando catálogo de servicios...")
            for name, desc, price, dur in DEFAULT_SERVICES:
                cursor.execute(
                    "INSERT INTO services (name, description, price, duration_minutes) VALUES (%s, %s, %s, %s);",
                    (name, desc, price, dur)
                )

        if "--reset" in sys.argv or "reset" in sys.argv:
            print("Limpiando citas y todos los usuarios de prueba...")
            cursor.execute("TRUNCATE users, appointments RESTART IDENTITY CASCADE;")

        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'superadmin';")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO users (name, email, phone, birthdate, password_hash, role, is_verified) VALUES (%s, %s, %s, %s, %s, %s, TRUE);",
                ("Dra. Admin GINEMEDIK", "admin@ginemedik.com", "5555-0000", "1985-05-15", hash_password("admin123"), "superadmin")
            )

        conn.commit()
        print("¡Base de datos DESA inicializada desde 0 exitosamente!")
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error actualizando tablas: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    pwd = sys.argv[1] if len(sys.argv) > 1 else None
    init_database(pwd)
