# Aptimizer — single image: React build served by nginx, FastAPI behind it on /api.
# One service, one URL, same origin. Deploys as-is to Render, Railway, Fly or any VPS.

# ---- 1. build the web app -------------------------------------------------
FROM node:20-slim AS web
WORKDIR /web

COPY frontend/package.json frontend/package-lock.json ./

# Two verified quirks in this dependency tree:
#   @emergentbase/visual-edits is fetched from assets.emergent.sh, unreachable from
#   most build environments; craco.config.js already degrades gracefully without it.
#   react-day-picker's peer range conflicts with date-fns, so strict `npm ci` refuses.
RUN npm pkg delete 'devDependencies.@emergentbase/visual-edits' \
 && npm install --legacy-peer-deps --no-audit --no-fund

COPY frontend/ ./

# Empty on purpose: api.js builds `${REACT_APP_BACKEND_URL}/api`, so this yields the
# relative path /api, which nginx proxies to the API on the same origin.
ENV REACT_APP_BACKEND_URL=""
ENV CI=false
RUN npm run build

# ---- 2. runtime -----------------------------------------------------------
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      nginx gettext-base curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./

COPY --from=web /web/build /var/www/aptimizer
COPY deploy/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY deploy/start.sh /start.sh
RUN chmod +x /start.sh

# Hosts inject their own port; 8080 is the local default.
ENV PORT=8080
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
  CMD curl -fsS "http://localhost:${PORT}/api/" || exit 1

CMD ["/start.sh"]
