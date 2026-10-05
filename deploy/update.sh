#!/usr/bin/env bash
# Update SIRIUS from GitHub: pull, install dependencies, migrate, build frontend, restart.
# Usage (as root): /opt/sirius/app/deploy/update.sh
set -euo pipefail
APP=/opt/sirius/app
BACKEND=$APP/backend/hackathon-hospital
FRONTEND=$APP/frontend/SberMedAI

echo "==> Pulling latest code"
sudo -u sirius git -C "$APP" pull --ff-only

echo "==> Backend dependencies and migrations"
sudo -u sirius /opt/sirius/venv/bin/pip install -q -r "$BACKEND/requirements.txt"
sudo -u sirius bash -c "set -a; source /etc/sirius/backend.env; set +a; cd '$BACKEND' && /opt/sirius/venv/bin/alembic upgrade head"

echo "==> Building frontend"
sudo -u sirius bash -c "cd '$FRONTEND' && npm ci --no-audit --no-fund && VITE_API_URL=/api npm run build"

echo "==> Restarting services"
cp "$APP/deploy/sirius-backend.service" /etc/systemd/system/sirius-backend.service
cp "$APP/deploy/nginx-sirius.conf" /etc/nginx/sites-available/sirius
systemctl daemon-reload
systemctl restart sirius-backend
nginx -t && systemctl reload nginx
# The backend needs a few seconds to import its dependencies.
for i in $(seq 1 30); do
    if curl -fsS http://127.0.0.1/api/ >/dev/null 2>&1; then echo "==> OK: SIRIUS is up"; exit 0; fi
    sleep 1
done
echo "==> Backend did not answer within 30 s"
journalctl -u sirius-backend -n 30 --no-pager
exit 1
