#!/bin/sh
set -e

: "${PORT:=8080}"
export PORT

# Only ${PORT} is substituted; nginx's own $variables must survive untouched.
envsubst '${PORT}' < /etc/nginx/templates/default.conf.template \
  > /etc/nginx/conf.d/default.conf
rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

echo "Starting API on 127.0.0.1:8000"
uvicorn server:app --host 127.0.0.1 --port 8000 --workers 2 &
API_PID=$!

# If the API dies, take the whole container down so the host restarts it, rather
# than serving a web app whose every request 502s.
trap 'kill -TERM $API_PID 2>/dev/null' TERM INT

echo "Starting web server on :${PORT}"
nginx -g 'daemon off;' &
NGINX_PID=$!

wait -n $API_PID $NGINX_PID
exit $?
