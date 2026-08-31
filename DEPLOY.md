# Deploying Aptimizer

Goal: reach Aptimizer from any machine — MacBook, Windows PC, phone — through a URL, without setting up a development environment on each one.

The stack is three containers: **Mongo** (data), **backend** (FastAPI), **frontend** (the React build served by nginx, which also proxies `/api` to the backend). Because the web app and the API share one origin, there is no CORS configuration to get wrong.

---

## 1. Files this adds

```
docker-compose.yml          the whole stack
.env.example                every setting, documented — copy to .env
backend/Dockerfile          Python 3.11 + uvicorn, runs as a non-root user
backend/.dockerignore
frontend/Dockerfile         two stages: npm build, then nginx
frontend/nginx.conf         SPA routing, /api proxy, cache headers
frontend/.dockerignore
caddy/Caddyfile             automatic HTTPS, used only on a public server
```

Nothing in the application code changes. `.env` must never be committed — add it to `.gitignore` if it is not there already.

---

## 2. Run it on the MacBook first

Prove the stack works locally before paying for a server.

```bash
# 1. Docker Desktop for Mac — install from docker.com, then open it once.

# 2. Get the code and configure
git clone <your-repo-url> aptimizer && cd aptimizer
cp .env.example .env

# 3. Fill in three values in .env
#    JWT_SECRET       ->  openssl rand -hex 32
#    ADMIN_PASSWORD   ->  anything you will remember
#    GEMINI_API_KEY   ->  your key, for APT and the AI reports
#    If port 80 is busy on your Mac, also set WEB_PORT=8080

# 4. Build and start
docker compose up -d --build

# 5. Open it
open http://localhost        # or http://localhost:8080
```

First build takes 5–10 minutes — mostly `npm install`. Later builds are cached and take under a minute.

Useful commands:

```bash
docker compose logs -f backend     # follow API logs
docker compose ps                  # what is running
docker compose down                # stop, keep the data
docker compose down -v             # stop and delete the database
docker compose up -d --build       # rebuild after a code change
```

Apple Silicon needs nothing special — every base image used here is multi-architecture.

---

## 3. Put it on the internet

Two routes. Pick one.

### Route A — a VPS you control (recommended)

A €5/month box is more than enough for a small team. Hetzner, DigitalOcean and Vultr are all fine; pick a region near your users (for India, Bangalore or Singapore).

```bash
# On the server, as root:
curl -fsSL https://get.docker.com | sh

git clone <your-repo-url> aptimizer && cd aptimizer
cp .env.example .env
nano .env          # same three values, plus DOMAIN and LETSENCRYPT_EMAIL
```

For HTTPS, point an A record for your domain at the server's IP, then in `docker-compose.yml`:

- uncomment the whole `caddy:` service
- change the `frontend:` service from `ports: ["${WEB_PORT:-80}:80"]` to `expose: ["80"]`

Then:

```bash
docker compose up -d --build
```

Caddy obtains and renews the certificate automatically. `https://your-domain` works within a minute or two, from anywhere.

Firewall: open 22, 80 and 443, nothing else. Mongo is deliberately not published to the host — it is reachable only from the backend container.

### Route B — a managed platform (no server administration)

Render, Railway and Fly.io all deploy from a Dockerfile and terminate TLS for you. The shape is the same on each:

1. **Database** — MongoDB Atlas free tier. Create a cluster, add a database user, allow access from anywhere (or the platform's IP range), and copy the connection string into `MONGO_URL`.
2. **Backend service** — deploy from `backend/Dockerfile`, set every variable from `.env.example`, expose port 8000.
3. **Frontend service** — deploy from `frontend/Dockerfile`. Because the two services are on different hostnames here, the same-origin trick does not apply: set `REACT_APP_BACKEND_URL` to the backend's public URL as a **build argument**, and set `FRONTEND_URL` on the backend to the frontend's URL so CORS allows it.

Route B costs more per month than Route A and gives you less control, but there is no server to patch.

---

## 4. Before anyone else uses it

- **`JWT_SECRET` must be unique and secret.** Anyone holding it can mint valid sign-in tokens for any account.
- **Change `ADMIN_PASSWORD` after the first sign-in**, and remove it from `.env` afterwards — it is only read at first startup.
- **Back up the database.** `docker compose exec -T mongo mongodump --archive` piped to a dated file, on a cron. An untested backup is not a backup; restore one before you rely on it.
- **Watch the AI spend.** Every APT message and AI report is a paid API call. Set a billing alert at the provider.
- **The reports are design assistance, not certification.** If people outside your team will act on them, put that in writing in the product, not only in APT's replies.

---

## 5. Updating a running deployment

```bash
git pull
docker compose up -d --build
```

Containers are replaced one at a time; Mongo keeps its volume, so data survives. Roll back with `git checkout <previous-commit>` and the same command.

---

## 6. What this is not

This is single-tenant: one deployment, one organisation, everyone who signs in shares the same project space subject to the existing sharing rules. That is the right shape for your own use and for one firm.

Selling it to multiple firms is a different piece of work — per-organisation data isolation, signup and billing, usage caps on the LLM calls, an admin console, and a legal review of how IS/NBC clause content is stored. Do not put this deployment in front of paying customers as-is.
