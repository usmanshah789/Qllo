# Deploying

Two services: a FastAPI API and a static React site. `render.yaml` defines both.

## 1. Push to GitHub

Create an empty repository on github.com — no README, no .gitignore, this
repository already has them. Then:

```bash
cd D:\Qloo
git remote add origin https://github.com/<you>/<repo>.git
git branch -M main
git push -u origin main
```

`.env` is in `.gitignore`, so your keys stay on your machine. Check before you
push:

```bash
git status --short
```

If `.env` appears in that list, stop and fix `.gitignore` first.

## 2. Deploy on Render

1. Go to [dashboard.render.com](https://dashboard.render.com) → **New** →
   **Blueprint**
2. Connect the repository. Render reads `render.yaml` and proposes two
   services: `taste-agent-api` and `taste-agent-web`
3. It will ask for the two secrets, because they are marked `sync: false`:
   - `QLOO_API_KEY`
   - `GROQ_API_KEY`
4. **Apply**

The API answers on `/api/health`, which is also its health check. The static
site gets `VITE_API_URL` pointing at the API, and the API gets `CORS_ORIGINS`
pointing back at the site — Render wires both automatically.

## 3. Check it

```bash
curl https://taste-agent-api.onrender.com/api/health
```

Expect `"mode": "live"` and `"brain": "groq"`. If `mode` says `mock`, the Qloo
key did not reach the service; if `brain` says `rules`, the Groq key did not.

Then open the static site and send a message.

## Things worth knowing

**First request is slow.** Render's free plan sleeps a service after 15 minutes
of no traffic, and the next request waits ~50s for it to wake. Open the site a
minute before a demo.

**Sessions do not survive a deploy.** They are written to `DATA_DIR`
(`/tmp/taste-agent` by default), which Render wipes on each deploy and on
restart. Attach a Render Disk and point `DATA_DIR` at it if you need them kept.

**Groq's free tier allows 8000 tokens per minute.** The backend reads the
remaining budget from each response and waits rather than overrunning it, but
several people using the demo at once will still feel it. The rule-based brain
answers whenever the model cannot.

**Both services must deploy.** If only the API is up, the site shows
"Backend unreachable"; if only the site is up, every message fails.
