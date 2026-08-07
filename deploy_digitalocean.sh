#!/bin/bash
set -e

export DEBIAN_FRONTEND=noninteractive

echo "=== INICIANDO INSTALACIÓN DE GINEMEDIK EN DIGITALOCEAN ==="

# 1. Actualizar paquetes del sistema
sudo apt update && sudo apt upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"

# 2. Instalar dependencias
sudo apt install -y python3 python3-pip postgresql postgresql-contrib nginx git

# 3. Iniciar servicio PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 4. Configurar base de datos y clave de PostgreSQL
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'ginemedik2026!';"
sudo -u postgres psql -c "CREATE DATABASE \"DESA\";" || true

# 5. Descargar repositorio de GitHub
sudo rm -rf /var/www/ginemedik
sudo git clone https://github.com/jos235felipe/clouddesa.git /var/www/ginemedik
cd /var/www/ginemedik

# 6. Instalar librerías de Python
sudo pip3 install psycopg2-binary --break-system-packages || sudo pip3 install psycopg2-binary

# 7. Crear archivo de variables de entorno (.env)
sudo bash -c 'cat <<EOF > /var/www/ginemedik/.env
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=DESA
DB_USER=postgres
DB_PASSWORD=ginemedik2026!
EOF'

# 8. Poblar la base de datos PostgreSQL
python3 init_db.py ginemedik2026!

# 9. Crear servicio de fondo Systemd (Servidor activo 24/7)
sudo bash -c 'cat <<EOF > /etc/systemd/system/ginemedik.service
[Unit]
Description=GINEMEDIK Python Web Server
After=network.target postgresql.service

[Service]
User=root
WorkingDirectory=/var/www/ginemedik
ExecStart=/usr/bin/python3 /var/www/ginemedik/server.py
Restart=always
RestartSec=5
Environment=DB_HOST=127.0.0.1
Environment=DB_PORT=5432
Environment=DB_NAME=DESA
Environment=DB_USER=postgres
Environment=DB_PASSWORD=ginemedik2026!

[Install]
WantedBy=multi-user.target
EOF'

sudo systemctl daemon-reload
sudo systemctl enable ginemedik
sudo systemctl restart ginemedik

# 10. Configurar Nginx Web Proxy
sudo bash -c 'cat <<EOF > /etc/nginx/sites-available/ginemedik
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name ginemedik.com www.ginemedik.com _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF'

sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/ginemedik /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

echo "=== ¡INSTALACIÓN DE GINEMEDIK COMPLETADA EXITOSAMENTE EN DIGITALOCEAN! ==="
