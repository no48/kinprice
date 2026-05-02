#!/bin/bash
# VPS initial setup script
# Usage: sudo bash setup.sh YOUR_DOMAIN

set -euo pipefail

DOMAIN="${1:?ドメインを指定してください（例: gold.example.com）}"
APP_DIR="/opt/gold-price-uploader"

echo "=== System update ==="
apt update && apt upgrade -y

echo "=== Install packages ==="
apt install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx ufw

echo "=== Firewall ==="
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

echo "=== Auto-updates ==="
apt install -y unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades

echo "=== App directory ==="
mkdir -p "$APP_DIR"
cp -r . "$APP_DIR/"

echo "=== Python venv ==="
cd "$APP_DIR"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo "=== .env check ==="
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo "WARNING: Edit .env file: $APP_DIR/.env"
fi

echo "=== Nginx config ==="
cp deploy/nginx.conf /etc/nginx/sites-available/gold-uploader
sed -i "s/YOUR_DOMAIN/$DOMAIN/g" /etc/nginx/sites-available/gold-uploader
ln -sf /etc/nginx/sites-available/gold-uploader /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo "=== SSL certificate ==="
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email admin@"$DOMAIN"

echo "=== Systemd service ==="
cp deploy/gold-uploader.service /etc/systemd/system/
chown -R www-data:www-data "$APP_DIR"
systemctl daemon-reload
systemctl enable gold-uploader
systemctl start gold-uploader

echo "=== Setup complete ==="
echo "Site: https://$DOMAIN"
echo ""
echo "Next steps:"
echo "1. Edit .env: $APP_DIR/.env"
echo "2. Restart: systemctl restart gold-uploader"
echo "3. Disable SSH password: PasswordAuthentication no in /etc/ssh/sshd_config"
