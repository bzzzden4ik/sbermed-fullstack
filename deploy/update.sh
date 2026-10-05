#!/usr/bin/env bash
# Update SIRIUS from GitHub: pull, install dependencies, migrate, index knowledge, build frontend, reload.
# Usage (as root): /opt/sirius/app/deploy/update.sh
# No downtime: the API workers are replaced gracefully and the new frontend is switched in atomically.
set -euo pipefail
APP=/opt/sirius/app
BACKEND=$APP/backend/hackathon-hospital
FRONTEND=$APP/frontend/SberMedAI
RELEASES=/opt/sirius/frontend/releases
CURRENT=/opt/sirius/frontend/current
ENV="set -a; source /etc/sirius/backend.env; set +a"

# Pull first, then restart this script so the freshly pulled version of it is what runs.
if [ "${SIRIUS_UPDATE_REEXEC:-}" != "1" ]; then
    echo "==> Pulling latest code"
    sudo -u sirius git -C "$APP" pull --ff-only
    SIRIUS_UPDATE_REEXEC=1 exec "$APP/deploy/update.sh" "$@"
fi

echo "==> Backend dependencies and migrations"
sudo -u sirius /opt/sirius/venv/bin/pip install -q -r "$BACKEND/requirements.txt"
sudo -u sirius bash -c "$ENV; cd '$BACKEND' && /opt/sirius/venv/bin/alembic upgrade head"

echo "==> Knowledge base (RAG): embedding new or changed sections"
sudo -u sirius bash -c "$ENV; cd '$BACKEND' && /opt/sirius/venv/bin/python ../../deploy/ingest_knowledge.py"

echo "==> Building frontend into a new release"
RELEASE="$RELEASES/$(date +%Y%m%d-%H%M%S)"
install -d -o sirius -g sirius "$RELEASES"
sudo -u sirius bash -c "cd '$FRONTEND' && npm ci --no-audit --no-fund --loglevel=error && VITE_API_URL=/api npx vite build --outDir '$RELEASE' --emptyOutDir --logLevel warn"
# Atomic switch: visitors get either the old or the new release, never a mix.
ln -sfn "$RELEASE" "$CURRENT.tmp" && mv -Tf "$CURRENT.tmp" "$CURRENT"
ls -1dt "$RELEASES"/* | tail -n +4 | xargs -r rm -rf   # keep the last 3 releases

echo "==> Installing service configuration"
UNITS_CHANGED=0
for unit in sirius-backend.service sirius-mcp.service; do
    if ! cmp -s "$APP/deploy/$unit" "/etc/systemd/system/$unit"; then
        cp "$APP/deploy/$unit" "/etc/systemd/system/$unit"
        UNITS_CHANGED=1
    fi
done
install -d /etc/systemd/journald.conf.d
if ! cmp -s "$APP/deploy/journald-sirius.conf" /etc/systemd/journald.conf.d/sirius.conf; then
    cp "$APP/deploy/journald-sirius.conf" /etc/systemd/journald.conf.d/sirius.conf
    systemctl restart systemd-journald
fi
cp "$APP/deploy/nginx-sirius.conf" /etc/nginx/sites-available/sirius
systemctl daemon-reload
systemctl enable sirius-backend sirius-mcp >/dev/null 2>&1

echo "==> Reloading services"
if [ "$UNITS_CHANGED" = "1" ] || ! systemctl is-active --quiet sirius-backend; then
    systemctl restart sirius-backend
else
    systemctl reload sirius-backend   # graceful: new workers start, old ones finish their requests
fi
systemctl restart sirius-mcp            # AI tool calls only; back within a few seconds
nginx -t && systemctl reload nginx

# The backend needs a few seconds to import its dependencies.
for i in $(seq 1 45); do
    # API (4 workers), MCP for the AI agents, then the public site through Nginx.
    if curl -fsS http://127.0.0.1:8000/ >/dev/null 2>&1 && curl -fsS http://127.0.0.1:8001/ >/dev/null 2>&1 \
        && curl -fsS -o /dev/null https://sirius.data-cdn.top/api/; then
        echo "==> OK: SIRIUS is up at https://sirius.data-cdn.top"; exit 0
    fi
    sleep 1
done
echo "==> Services did not answer within 45 s"
journalctl -u sirius-backend -u sirius-mcp -n 40 --no-pager
exit 1
