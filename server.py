import http.server
import socketserver
import json
import urllib.parse
import urllib.request
import sys
import os
import re
import datetime
import hashlib
import random
import psycopg2

PORT = 5000

DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
DB_PORT = int(os.environ.get("DB_PORT", 5432))
DB_NAME = os.environ.get("DB_NAME", "DESA")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "citas@ginemedik.com")
SENDER_NAME = os.environ.get("SENDER_NAME", "GINEMEDIK Clínica")

def send_brevo_token_email(to_email, to_name, token):
    if not BREVO_API_KEY:
        print(f"[Aviso Email] BREVO_API_KEY no configurada. Token para {to_email}: {token}")
        return False

    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }

    html_content = f"""
    <div style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; max-width: 520px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 16px; padding: 28px; background: #ffffff; box-shadow: 0 10px 25px rgba(0,82,165,0.08);">
      <div style="text-align: center; padding-bottom: 16px; border-bottom: 2px solid #f1f5f9;">
        <h2 style="color: #0052A5; margin: 0; font-size: 24px; font-weight: 800;">GINEMEDIK</h2>
        <p style="color: #00ADEF; font-size: 13px; font-weight: 700; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px;">Centro Médico Ginecológico & Obstétrico</p>
      </div>
      <div style="padding: 20px 0;">
        <h3 style="color: #0F172A; margin-top: 0;">¡Hola, {to_name}! 🌸</h3>
        <p style="color: #475569; font-size: 15px; line-height: 1.6;">Tu código de verificación de 6 dígitos para activar tu cuenta en el portal médico de <strong>GINEMEDIK</strong> es:</p>
        <div style="background: #E8F7FC; border: 2px dashed #00ADEF; padding: 20px; text-align: center; border-radius: 12px; margin: 24px 0;">
          <span style="font-size: 32px; font-weight: 800; letter-spacing: 10px; color: #0052A5;">{token}</span>
        </div>
        <p style="color: #64748B; font-size: 13px; line-height: 1.5;">Ingresa este código en la pantalla de confirmación para activar tu cuenta e iniciar sesión.</p>
      </div>
      <div style="border-top: 1px solid #f1f5f9; padding-top: 16px; text-align: center; color: #94A3B8; font-size: 12px;">
        <p style="margin: 0;">&copy; 2026 GINEMEDIK - Cuidado integral para la mujer.</p>
      </div>
    </div>
    """

    senders = [SENDER_EMAIL, "josfelipe235@gmail.com"]
    for s_email in senders:
        if not s_email:
            continue
        payload = {
            "sender": {"name": SENDER_NAME, "email": s_email},
            "to": [{"email": to_email, "name": to_name}],
            "subject": f"🔐 Tu Código de Verificación GINEMEDIK: {token}",
            "htmlContent": html_content
        }

        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
            with urllib.request.urlopen(req) as resp:
                print(f"[Email Brevo Enviado] Token enviado exitosamente a {to_email} usando {s_email}")
                return True
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode('utf-8', errors='ignore')
            print(f"[Error Brevo {e.code}] Con remitente {s_email}: {err_msg}")
        except Exception as e:
            print(f"[Error Brevo Excepcion] Con remitente {s_email}: {e}")

    return False

def get_db():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        return None

FALLBACK_USERS = [
    {
        "id": 1,
        "name": "Dra. Admin GINEMEDIK",
        "email": "admin@ginemedik.com",
        "phone": "5555-0000",
        "birthdate": "1985-05-15",
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "superadmin",
        "is_verified": True,
        "verification_token": None,
        "verification_method": "email"
    },
    {
        "id": 2,
        "name": "María López",
        "email": "paciente@ginemedik.com",
        "phone": "5555-1234",
        "birthdate": "1994-08-20",
        "password_hash": hashlib.sha256("paciente123".encode()).hexdigest(),
        "role": "paciente",
        "is_verified": True,
        "verification_token": None,
        "verification_method": "email"
    }
]

FALLBACK_SERVICES = [
    {"id": 1, "name": "Consulta", "description": "Consulta médica especializada ginecológica y obstetricia con revisión integral.", "price": 190.00, "duration_minutes": 30},
    {"id": 2, "name": "Papanicolaou", "description": "Examen de Papanicolaou (Citología cérvico-vaginal) para prevención y diagnóstico.", "price": 130.00, "duration_minutes": 30},
    {"id": 3, "name": "Ultrasonido", "description": "Ultrasonido pélvico / obstétrico / ginecológico de alta definición.", "price": 200.00, "duration_minutes": 30},
    {"id": 4, "name": "Consulta + Ultrasonido", "description": "Evaluación médica completa combinada con examen de ultrasonido.", "price": 390.00, "duration_minutes": 30},
    {"id": 5, "name": "Consulta + Ultrasonido + Papanicolaou", "description": "Chequeo ginecológico integral completo.", "price": 430.00, "duration_minutes": 60}
]

FALLBACK_APPOINTMENTS = [
    {
        "id": 1,
        "patient_id": 2,
        "patient_name": "María López",
        "patient_phone": "5555-1234",
        "patient_email": "paciente@ginemedik.com",
        "service_id": 4,
        "service_name": "Consulta + Ultrasonido",
        "price": 390.00,
        "appointment_date": (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
        "start_time": "09:00",
        "end_time": "09:30",
        "status": "confirmada",
        "notes": "Primera consulta de control"
    }
]

FALLBACK_BLOCKS = []

def hash_pw(pw):
    return hashlib.sha256(pw.encode('utf-8')).hexdigest()

def generate_token():
    return str(random.randint(100000, 999999))

def time_to_minutes(t_str):
    if isinstance(t_str, datetime.time):
        return t_str.hour * 60 + t_str.minute
    parts = str(t_str).split(":")
    return int(parts[0]) * 60 + int(parts[1])

def minutes_to_time(mins):
    h = mins // 60
    m = mins % 60
    return f"{h:02d}:{m:02d}"

def get_slots_for_date(date_str, duration_minutes=30):
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return []

    weekday = dt.weekday()
    if weekday == 6: # Domingo cerrado
        return []

    start_hour = 8
    end_hour = 17 if weekday < 5 else 13 # L-V 8-17, Sáb 8-13

    slots = []
    current_min = start_hour * 60
    end_min = end_hour * 60

    while current_min < end_min:
        slot_end = current_min + duration_minutes
        if slot_end <= end_min:
            slots.append({
                "start_time": minutes_to_time(current_min),
                "end_time": minutes_to_time(slot_end),
                "start_min": current_min,
                "end_min": slot_end
            })
        current_min += 30 # Intervalos de selección a las :00 y :30

    return slots

class GinemedikRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def parse_body(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length).decode('utf-8')
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/api/health":
            conn = get_db()
            db_status = "connected" if conn else "using_memory_store"
            if conn:
                conn.close()
            return self.send_json({"status": "ok", "database": db_status})

        elif path == "/api/services":
            conn = get_db()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, name, description, price, duration_minutes FROM services ORDER BY id;")
                rows = cursor.fetchall()
                services = []
                for r in rows:
                    dur = r[4] if r[4] else (60 if ("Papanicolaou" in r[1] and "Ultrasonido" in r[1]) else 30)
                    services.append({"id": r[0], "name": r[1], "description": r[2], "price": float(r[3]), "duration_minutes": dur})
                cursor.close()
                conn.close()
                return self.send_json(services)
            else:
                return self.send_json(FALLBACK_SERVICES)

        elif path == "/api/appointments/available-slots":
            date_str = query.get("date", [None])[0]
            duration_minutes = int(query.get("duration", [30])[0])

            if not date_str:
                return self.send_json({"error": "Debe especificar una fecha (date=YYYY-MM-DD)"}, code=400)

            all_slots = get_slots_for_date(date_str, duration_minutes)
            conn = get_db()

            occupied_ranges = []

            if conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT start_time, end_time FROM appointments WHERE appointment_date = %s AND status != 'cancelada';",
                    (date_str,)
                )
                for r in cursor.fetchall():
                    st_m = time_to_minutes(r[0])
                    et_m = time_to_minutes(r[1])
                    occupied_ranges.append((st_m, et_m))

                cursor.execute(
                    "SELECT start_time, end_time FROM schedule_blocks WHERE block_date = %s;",
                    (date_str,)
                )
                for r in cursor.fetchall():
                    st_m = time_to_minutes(r[0])
                    et_m = time_to_minutes(r[1])
                    occupied_ranges.append((st_m, et_m))

                cursor.close()
                conn.close()
            else:
                for appt in FALLBACK_APPOINTMENTS:
                    if appt["appointment_date"] == date_str and appt["status"] != "cancelada":
                        st_m = time_to_minutes(appt["start_time"])
                        et_m = time_to_minutes(appt["end_time"])
                        occupied_ranges.append((st_m, et_m))
                for b in FALLBACK_BLOCKS:
                    if b["block_date"] == date_str:
                        st_m = time_to_minutes(b["start_time"])
                        et_m = time_to_minutes(b["end_time"])
                        occupied_ranges.append((st_m, et_m))

            result_slots = []
            for slot in all_slots:
                s_start = slot["start_min"]
                s_end = slot["end_min"]
                
                # Verificar solapamiento con rangos ocupados
                is_available = True
                for o_start, o_end in occupied_ranges:
                    if not (s_end <= o_start or s_start >= o_end):
                        is_available = False
                        break

                result_slots.append({
                    "start_time": slot["start_time"],
                    "end_time": slot["end_time"],
                    "available": is_available
                })

            return self.send_json({"date": date_str, "duration_minutes": duration_minutes, "slots": result_slots})

        elif path == "/api/appointments/my":
            email = query.get("email", [None])[0]
            if not email:
                return self.send_json({"error": "Email requerido"}, code=400)

            conn = get_db()
            if conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, patient_name, patient_email, patient_phone, service_name, price, appointment_date, start_time, end_time, status, notes FROM appointments WHERE patient_email = %s ORDER BY appointment_date DESC, start_time DESC;",
                    (email,)
                )
                rows = cursor.fetchall()
                appts = []
                for r in rows:
                    appts.append({
                        "id": r[0],
                        "patient_name": r[1],
                        "patient_email": r[2],
                        "patient_phone": r[3],
                        "service_name": r[4],
                        "price": float(r[5]),
                        "appointment_date": r[6].strftime("%Y-%m-%d") if hasattr(r[6], 'strftime') else str(r[6]),
                        "start_time": r[7].strftime("%H:%M") if hasattr(r[7], 'strftime') else str(r[7])[:5],
                        "end_time": r[8].strftime("%H:%M") if hasattr(r[8], 'strftime') else str(r[8])[:5],
                        "status": r[9],
                        "notes": r[10]
                    })
                cursor.close()
                conn.close()
                return self.send_json(appts)
            else:
                user_appts = [a for a in FALLBACK_APPOINTMENTS if a.get("patient_email") == email]
                return self.send_json(user_appts)

        elif path == "/api/admin/appointments":
            conn = get_db()
            if conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, patient_name, patient_email, patient_phone, service_name, price, appointment_date, start_time, end_time, status, notes FROM appointments ORDER BY appointment_date DESC, start_time DESC;"
                )
                rows = cursor.fetchall()
                appts = []
                for r in rows:
                    appts.append({
                        "id": r[0],
                        "patient_name": r[1],
                        "patient_email": r[2],
                        "patient_phone": r[3],
                        "service_name": r[4],
                        "price": float(r[5]),
                        "appointment_date": r[6].strftime("%Y-%m-%d") if hasattr(r[6], 'strftime') else str(r[6]),
                        "start_time": r[7].strftime("%H:%M") if hasattr(r[7], 'strftime') else str(r[7])[:5],
                        "end_time": r[8].strftime("%H:%M") if hasattr(r[8], 'strftime') else str(r[8])[:5],
                        "status": r[9],
                        "notes": r[10]
                    })
                cursor.close()
                conn.close()
                return self.send_json(appts)
            else:
                return self.send_json(FALLBACK_APPOINTMENTS)

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self.parse_body()

        if path == "/api/auth/register":
            name = body.get("name", "").strip()
            email = body.get("email", "").strip().lower()
            phone = body.get("phone", "").strip()
            birthdate = body.get("birthdate", "").strip()
            password = body.get("password", "")
            method = body.get("verification_method", "email").strip().lower()

            if not name or not email or not password or not birthdate:
                return self.send_json({"error": "Por favor completa todos los campos obligatorios incluyendo la fecha de nacimiento."}, code=400)

            token = generate_token()
            conn = get_db()
            p_hash = hash_pw(password)

            if conn:
                cursor = conn.cursor()
                try:
                    cursor.execute("SELECT id, is_verified FROM users WHERE email = %s;", (email,))
                    row = cursor.fetchone()
                    if row:
                        user_id, is_verified = row[0], row[1]
                        if is_verified:
                            return self.send_json({"error": "Este correo electrónico ya está registrado e instalado. Por favor inicia sesión con tu contraseña."}, code=400)
                        else:
                            # Cuenta pendiente de verificación: actualizar credenciales y token nuevo
                            cursor.execute(
                                """
                                UPDATE users SET name = %s, phone = %s, birthdate = %s, password_hash = %s, verification_token = %s, verification_method = %s
                                WHERE id = %s;
                                """,
                                (name, phone, birthdate, p_hash, token, method, user_id)
                            )
                    else:
                        cursor.execute(
                            """
                            INSERT INTO users (name, email, phone, birthdate, password_hash, role, is_verified, verification_token, verification_method)
                            VALUES (%s, %s, %s, %s, %s, 'paciente', FALSE, %s, %s) RETURNING id;
                            """,
                            (name, email, phone, birthdate, p_hash, token, method)
                        )
                    conn.commit()

                    dest_name = "tu correo electrónico" if method == "email" else f"tu WhatsApp ({phone})"
                    if method == "email":
                        send_brevo_token_email(email, name, token)

                    return self.send_json({
                        "requires_verification": True,
                        "email": email,
                        "phone": phone,
                        "verification_method": method,
                        "message": f"Te hemos enviado un nuevo código de activación a {dest_name}."
                    })
                except Exception as e:
                    conn.rollback()
                    return self.send_json({"error": f"Error al registrar: {e}"}, code=500)
                finally:
                    cursor.close()
                    conn.close()
            else:
                for u in FALLBACK_USERS:
                    if u["email"] == email:
                        if u.get("is_verified", True):
                            return self.send_json({"error": "Este correo electrónico ya está registrado."}, code=400)
                        else:
                            u["verification_token"] = token
                            u["name"] = name
                            u["phone"] = phone
                            u["password_hash"] = p_hash
                            if method == "email":
                                send_brevo_token_email(email, name, token)
                            return self.send_json({
                                "requires_verification": True,
                                "email": email,
                                "message": "Te hemos reenviado un nuevo código de activación."
                            })

        elif path == "/api/auth/resend-token":
            email = body.get("email", "").strip().lower()
            if not email:
                return self.send_json({"error": "Ingresa tu correo electrónico."}, code=400)

            token = generate_token()
            conn = get_db()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, name, is_verified FROM users WHERE email = %s;", (email,))
                row = cursor.fetchone()
                if not row:
                    cursor.close()
                    conn.close()
                    return self.send_json({"error": "Usuario no encontrado."}, code=404)

                user_id, name, is_verified = row[0], row[1], row[2]
                if is_verified:
                    cursor.close()
                    conn.close()
                    return self.send_json({"error": "Esta cuenta ya está verificada. Puedes iniciar sesión directamente."}, code=400)

                cursor.execute("UPDATE users SET verification_token = %s WHERE id = %s;", (token, user_id))
                conn.commit()
                cursor.close()
                conn.close()

                send_brevo_token_email(email, name, token)
                return self.send_json({"message": f"¡Código nuevo enviado a {email}!"})
            else:
                return self.send_json({"error": "Servicio de base de datos no disponible."}, code=500)

        elif path == "/api/auth/verify-token":
            email = body.get("email", "").strip().lower()
            token = body.get("token", "").strip()

            if not email or not token:
                return self.send_json({"error": "Ingresa el correo y el código de verificación de 6 dígitos."}, code=400)

            conn = get_db()
            if conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, name, email, phone, birthdate, role, verification_token FROM users WHERE email = %s;",
                    (email,)
                )
                row = cursor.fetchone()
                if not row:
                    cursor.close()
                    conn.close()
                    return self.send_json({"error": "Usuario no encontrado."}, code=404)

                stored_token = row[6]
                if stored_token != token:
                    cursor.close()
                    conn.close()
                    return self.send_json({"error": "El código de verificación ingresado es incorrecto. Intenta de nuevo."}, code=400)

                cursor.execute(
                    "UPDATE users SET is_verified = TRUE, verification_token = NULL WHERE id = %s;",
                    (row[0],)
                )
                conn.commit()
                cursor.close()
                conn.close()

                return self.send_json({
                    "message": "¡Cuenta verificada exitosamente!",
                    "user": {"id": row[0], "name": row[1], "email": row[2], "phone": row[3], "birthdate": str(row[4]), "role": row[5]}
                })
            else:
                for u in FALLBACK_USERS:
                    if u["email"] == email:
                        if u.get("verification_token") == token:
                            u["is_verified"] = True
                            u["verification_token"] = None
                            return self.send_json({
                                "message": "¡Cuenta verificada exitosamente!",
                                "user": {"id": u["id"], "name": u["name"], "email": u["email"], "phone": u["phone"], "birthdate": u.get("birthdate", ""), "role": u["role"]}
                            })
                        else:
                            return self.send_json({"error": "El código de verificación ingresado es incorrecto."}, code=400)
                return self.send_json({"error": "Usuario no encontrado."}, code=404)

        elif path == "/api/auth/login":
            email = body.get("email", "").strip().lower()
            password = body.get("password", "")

            if not email or not password:
                return self.send_json({"error": "Ingresa tu usuario y contraseña."}, code=400)

            p_hash = hash_pw(password)
            conn = get_db()

            if conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, name, email, phone, birthdate, role, password_hash, is_verified, verification_token FROM users WHERE email = %s;",
                    (email,)
                )
                row = cursor.fetchone()
                cursor.close()
                conn.close()
                if not row or row[6] != p_hash:
                    return self.send_json({"error": "Credenciales incorrectas. Verifica tu correo y contraseña."}, code=401)
                
                is_verified = row[7]
                if not is_verified:
                    return self.send_json({
                        "requires_verification": True,
                        "email": email,
                        "error": "Tu cuenta aún no ha sido verificada. Ingresa el código de activación enviado."
                    }, code=403)

                return self.send_json({
                    "message": "Login exitoso",
                    "user": {"id": row[0], "name": row[1], "email": row[2], "phone": row[3], "birthdate": str(row[4]) if row[4] else "", "role": row[5]}
                })
            else:
                for u in FALLBACK_USERS:
                    if u["email"] == email and u["password_hash"] == p_hash:
                        if not u.get("is_verified", True):
                            return self.send_json({
                                "requires_verification": True,
                                "email": email,
                                "error": "Tu cuenta aún no ha sido verificada."
                            }, code=403)

                        return self.send_json({
                            "message": "Login exitoso",
                            "user": {"id": u["id"], "name": u["name"], "email": u["email"], "phone": u.get("phone", ""), "birthdate": u.get("birthdate", ""), "role": u["role"]}
                        })
                return self.send_json({"error": "Credenciales incorrectas. Verifica tu correo y contraseña."}, code=401)

        elif path == "/api/appointments":
            patient_name = body.get("patient_name", "").strip()
            patient_email = body.get("patient_email", "").strip()
            patient_phone = body.get("patient_phone", "").strip()
            service_id = body.get("service_id")
            service_name = body.get("service_name", "").strip()
            price = body.get("price", 0.0)
            date_str = body.get("appointment_date", "").strip()
            start_time = body.get("start_time", "").strip()
            notes = body.get("notes", "").strip()

            # Calcular duración según el servicio
            duration_minutes = 60 if ("Papanicolaou" in service_name and "Ultrasonido" in service_name) else 30

            if not patient_email or not service_name or not date_str or not start_time:
                return self.send_json({"error": "Faltan datos obligatorios para la cita."}, code=400)

            st_mins = time_to_minutes(start_time)
            et_mins = st_mins + duration_minutes
            end_time = minutes_to_time(et_mins)

            conn = get_db()
            if conn:
                cursor = conn.cursor()
                try:
                    # Comprobar si hay alguna cita existente que se solape en [st_mins, et_mins)
                    cursor.execute(
                        "SELECT start_time, end_time FROM appointments WHERE appointment_date = %s AND status != 'cancelada';",
                        (date_str,)
                    )
                    for r in cursor.fetchall():
                        o_st = time_to_minutes(r[0])
                        o_et = time_to_minutes(r[1])
                        if not (et_mins <= o_st or st_mins >= o_et):
                            return self.send_json({"error": "Este horario ya está ocupado o no cuenta con el tiempo completo disponible, por favor selecciona otro horario."}, code=409)

                    cursor.execute(
                        "SELECT start_time, end_time FROM schedule_blocks WHERE block_date = %s;",
                        (date_str,)
                    )
                    for r in cursor.fetchall():
                        o_st = time_to_minutes(r[0])
                        o_et = time_to_minutes(r[1])
                        if not (et_mins <= o_st or st_mins >= o_et):
                            return self.send_json({"error": "Este horario está bloqueado por la clínica, por favor selecciona otro disponible."}, code=409)

                    cursor.execute(
                        """
                        INSERT INTO appointments 
                        (patient_name, patient_phone, patient_email, service_id, service_name, price, appointment_date, start_time, end_time, status, notes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'confirmada', %s)
                        RETURNING id;
                        """,
                        (patient_name, patient_phone, patient_email, service_id, service_name, price, date_str, start_time, end_time, notes)
                    )
                    new_id = cursor.fetchone()[0]
                    conn.commit()
                    return self.send_json({
                        "message": "¡Cita agendada exitosamente en GINEMEDIK!",
                        "appointment": {
                            "id": new_id,
                            "patient_name": patient_name,
                            "service_name": service_name,
                            "price": price,
                            "appointment_date": date_str,
                            "start_time": start_time,
                            "end_time": end_time,
                            "status": "confirmada"
                        }
                    })
                except Exception as e:
                    conn.rollback()
                    return self.send_json({"error": f"Error al agendar cita: {e}"}, code=500)
                finally:
                    cursor.close()
                    conn.close()
            else:
                for a in FALLBACK_APPOINTMENTS:
                    if a["appointment_date"] == date_str and a["status"] != "cancelada":
                        o_st = time_to_minutes(a["start_time"])
                        o_et = time_to_minutes(a["end_time"])
                        if not (et_mins <= o_st or st_mins >= o_et):
                            return self.send_json({"error": "Este horario ya está ocupado o no cuenta con el tiempo completo disponible, por favor selecciona otro horario."}, code=409)

                new_appt = {
                    "id": len(FALLBACK_APPOINTMENTS) + 1,
                    "patient_id": body.get("patient_id", 2),
                    "patient_name": patient_name,
                    "patient_phone": patient_phone,
                    "patient_email": patient_email,
                    "service_id": service_id,
                    "service_name": service_name,
                    "price": float(price),
                    "appointment_date": date_str,
                    "start_time": start_time,
                    "end_time": end_time,
                    "status": "confirmada",
                    "notes": notes
                }
                FALLBACK_APPOINTMENTS.append(new_appt)
                return self.send_json({
                    "message": "¡Cita agendada exitosamente en GINEMEDIK!",
                    "appointment": new_appt
                })

        elif path == "/api/admin/bulk-import":
            citas_data = body.get("appointments", [])
            if not citas_data:
                return self.send_json({"error": "No se enviaron citas para importar."}, code=400)

            conn = get_db()
            imported_count = 0
            if conn:
                cursor = conn.cursor()
                try:
                    for c in citas_data:
                        s_name = c.get("service_name", "Consulta")
                        dur_mins = 60 if ("Papanicolaou" in s_name and "Ultrasonido" in s_name) else 30
                        sh, sm = map(int, c.get("start_time", "08:00").split(":"))
                        end_min = sh * 60 + sm + dur_mins
                        end_time = f"{end_min // 60:02d}:{end_min % 60:02d}"
                        
                        cursor.execute(
                            """
                            INSERT INTO appointments 
                            (patient_name, patient_phone, patient_email, service_name, price, appointment_date, start_time, end_time, status, notes)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'confirmada', %s)
                            ON CONFLICT (appointment_date, start_time) DO NOTHING;
                            """,
                            (
                                c.get("patient_name", "Paciente Importada"),
                                c.get("patient_phone", "5555-0000"),
                                c.get("patient_email", "importado@ginemedik.com"),
                                s_name,
                                c.get("price", 190.0),
                                c.get("appointment_date"),
                                c.get("start_time"),
                                end_time,
                                c.get("notes", "Importado masivamente / Google Calendar")
                            )
                        )
                        if cursor.rowcount > 0:
                            imported_count += 1
                    conn.commit()
                    return self.send_json({"message": f"Se importaron {imported_count} citas exitosamente en PostgreSQL DESA."})
                except Exception as e:
                    conn.rollback()
                    return self.send_json({"error": f"Error en la carga masiva: {e}"}, code=500)
                finally:
                    cursor.close()
                    conn.close()
            else:
                for c in citas_data:
                    s_name = c.get("service_name", "Consulta")
                    dur_mins = 60 if ("Papanicolaou" in s_name and "Ultrasonido" in s_name) else 30
                    sh, sm = map(int, c.get("start_time", "08:00").split(":"))
                    end_min = sh * 60 + sm + dur_mins
                    end_time = f"{end_min // 60:02d}:{end_min % 60:02d}"
                    FALLBACK_APPOINTMENTS.append({
                        "id": len(FALLBACK_APPOINTMENTS) + 1,
                        "patient_name": c.get("patient_name", "Paciente Importada"),
                        "patient_phone": c.get("patient_phone", "5555-0000"),
                        "patient_email": c.get("patient_email", "importado@ginemedik.com"),
                        "service_name": s_name,
                        "price": c.get("price", 190.0),
                        "appointment_date": c.get("appointment_date"),
                        "start_time": c.get("start_time"),
                        "end_time": end_time,
                        "status": "confirmada",
                        "notes": "Importado masivamente / Google Calendar"
                    })
                    imported_count += 1
                return self.send_json({"message": f"Se importaron {imported_count} citas exitosamente."})

        return self.send_json({"error": "Ruta no encontrada"}, code=404)

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print(f"Servidor GINEMEDIK corriendo en http://localhost:{PORT}")
    server = socketserver.TCPServer(("", PORT), GinemedikRequestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
