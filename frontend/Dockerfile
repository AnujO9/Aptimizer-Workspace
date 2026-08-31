# ---- build ----------------------------------------------------------------
FROM node:20-slim AS build
WORKDIR /app

COPY package.json package-lock.json ./

# Two quirks in this project's dependency tree, both verified:
#   1. @emergentbase/visual-edits is fetched from assets.emergent.sh, which is not
#      reachable from most build environments. craco.config.js already degrades
#      gracefully when it is absent (visual editing is simply disabled), so it is
#      removed here rather than failing the build.
#   2. react-day-picker's peer range conflicts with the installed date-fns, so a
#      strict `npm ci` refuses. --legacy-peer-deps is required.
RUN npm pkg delete 'devDependencies.@emergentbase/visual-edits' \
 && npm install --legacy-peer-deps --no-audit --no-fund

COPY . .

# Empty value on purpose: api.js builds `${REACT_APP_BACKEND_URL}/api`, so an empty
# string yields the relative path /api. nginx below proxies that to the API on the
# same origin, which removes CORS from the picture entirely.
ENV REACT_APP_BACKEND_URL=""
ENV CI=false
RUN npm run build

# ---- serve ----------------------------------------------------------------
FROM nginx:1.27-alpine
COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
