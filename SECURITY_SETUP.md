# Bot protection and abuse limits

Repo root: `D:\Workspace`. Wire up human verification on the public auth endpoints, add rate limits, and put the deployment behind a network edge.

**Read this distinction first, because it changes what you build.** A captcha and DDoS protection are different problems:

- A **captcha** stops *scripted abuse* — bulk account creation, credential stuffing, a bot burning your LLM budget. It works at the application layer, one request at a time.
- **DDoS protection** absorbs *volume*. By the time a request reaches Python, it has already taken a connection and a worker. No amount of captcha helps; the flood has to be stopped at the network edge, before it reaches the app.

So this is three pieces of work: verification (Step 1–3), rate limits (Step 4), and an edge (Step 5). Do all three; none substitutes for another.

## Standing rules

`grep -n` to locate, `sed -n 'X,Yp'` to read only what you need, targeted edits. Never read a whole file for a small change. Finish with `cd backend && python -m pytest -q` and `cd frontend && npm run build` both green. Commit once. Do not push.

---

## Step 1 — Backend verification module

`backend/turnstile.py` is provided alongside this file — copy it in as-is. It is complete and needs no changes. Read its docstring before wiring it up; the fail-open / fail-closed asymmetry is deliberate and must not be "fixed".

Cloudflare Turnstile is used rather than reCAPTCHA: free at any volume, no Google account, and invisible to most visitors — it scores the browser silently and only challenges when something looks automated.

Add nothing to `requirements.txt`; `httpx` is already there.

---

## Step 2 — Serve the site key at runtime, not build time

`REACT_APP_*` variables are baked into the bundle at build time, so putting the site key there means rebuilding the image to rotate a key. Avoid that.

Add an unauthenticated endpoint in `server.py`:

```
GET /api/public-config  ->  {"turnstile_site_key": "<key or empty string>"}
```

It returns `turnstile.site_key()`. An empty string means verification is off, and the frontend renders no widget. This is public information — the site key is visible in any page that uses it — so the endpoint needs no auth.

---

## Step 3 — Enforce it on the public auth routes

In `server.py`, `/auth/register` and `/auth/login` are the only unauthenticated write paths. Both take a captcha token.

- Add an optional `captcha_token: str = ""` field to `RegisterIn` and `LoginIn`.
- At the top of each handler, before touching the database:

```python
ok, reason = await turnstile.verify(body.captcha_token,
                                    request.client.host if request.client else None)
if not ok:
    raise HTTPException(status_code=400, detail=reason)
```

`/auth/register` currently has no `Request` parameter — add one. `/auth/login` already has it.

Verify **before** the existing login-attempt lookup, so a bot cannot burn a real user's lockout counter by submitting garbage against their email.

Leave `/auth/refresh` alone — it is authenticated by the refresh token and adding a captcha there would break silent session renewal.

---

## Step 4 — Frontend widget

In `Register.jsx` and `Login.jsx`:

- Fetch `/api/public-config` on mount. If `turnstile_site_key` is empty, render the form exactly as it is today and send no token — local development and any deployment without keys must keep working unchanged.
- Otherwise load `https://challenges.cloudflare.com/turnstile/v0/api.js` once (guard against double-injection when both pages mount in one session) and render the widget above the submit button.
- Keep submit **disabled** until the widget returns a token. This is the part that actually stops scripted signups — a form that submits without a token just gets a 400 and teaches the bot nothing.
- On a failed submit, reset the widget (`turnstile.reset()`), because a token is single-use. Without this, a user who mistypes a password cannot retry — the second attempt reuses a spent token and fails with "verification expired", which reads as a broken app.
- Show the backend's message on failure; `turnstile.py` already distinguishes an expired token from a rejected one.

---

## Step 5 — Rate limits

The captcha is bypassable by a determined attacker driving a real browser. Limits are what bound the damage.

**Application layer.** `/auth/login` already locks an identity out for 15 minutes after 5 failures. Add the equivalent for registration: cap new accounts per IP per hour (start at 5) in the same `login_attempts` collection pattern, and return 429 with a plain message. Also cap `POST /ai/chat` per user per hour — an authenticated abuser spending your LLM budget is the more expensive attack, and nothing currently stops it.

**Web server layer.** In `deploy/nginx.conf.template`, add a limit zone and apply it to the auth paths:

```
limit_req_zone $binary_remote_addr zone=auth:10m rate=10r/m;
limit_req_status 429;

location /api/auth/ {
    limit_req zone=auth burst=5 nodelay;
    proxy_pass http://127.0.0.1:8000;
    # ... keep the existing proxy headers
}
```

The zone directive goes at `http` level, so it needs a second template fragment or an `include` — check where nginx.conf includes this file and place it correctly rather than nesting it inside `server {}`, which will not start.

---

## Step 6 — The actual DDoS protection

Put the domain behind **Cloudflare's free plan**. This is the only part of this document that addresses volume.

1. Add the domain to Cloudflare, change nameservers at the registrar.
2. Set the DNS record for the app to **proxied** (orange cloud). Traffic now terminates at Cloudflare's edge, not your container.
3. Enable **Bot Fight Mode** and set Security Level to Medium.
4. Add a rate-limiting rule on `/api/auth/*` — Cloudflare's free tier includes one.
5. Once proxied, your origin should only accept Cloudflare traffic. On Render that means keeping the `.onrender.com` URL private and sharing only the custom domain; on a VPS, firewall port 443 to Cloudflare's published IP ranges.

Cloudflare in front is worth more than everything in Steps 1–5 combined for availability. Steps 1–5 are worth more for cost control and data integrity. They solve different problems.

---

## Configuration

Get keys at **dash.cloudflare.com → Turnstile → Add site**. Choose the **Managed** widget. You get a site key (public) and a secret key (private).

Add to `render.yaml` under `envVars`:

```yaml
      - key: TURNSTILE_SITE_KEY
        sync: false
      - key: TURNSTILE_SECRET_KEY
        sync: false
```

Both unset means verification is off — the intended state for local development. Set only one and it stays off by design; `turnstile.enabled()` requires both, because a secret without a site key would reject every real user while stopping no bots.

Cloudflare publishes test keys that always pass or always fail — use them to prove both paths before going live.

---

## Done when

- With no keys set, register and login behave exactly as they do today.
- With keys set, the widget appears, submit stays disabled until it solves, and a POST to `/api/auth/register` with no token returns 400.
- A failed sign-in can be retried without a page reload.
- The sixth registration from one IP within an hour returns 429.
- `nginx -t` passes and the container starts.
- pytest and `npm run build` both green.

Report at the end in under 10 lines: what shipped, files touched, test and build status, and confirmation that the no-keys path still works.
