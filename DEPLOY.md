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

One service, one URL. The Docker image builds the React app with Node and then
serves it from the same FastAPI process that answers `/api`, so there is no
second service to deploy and no CORS to configure.

1. [dashboard.render.com](https://dashboard.render.com) -> **New** ->
   **Blueprint**
2. Connect the repository. Render reads `render.yaml` and proposes one service,
   `taste-agent`
3. It asks for the two secrets, because they are marked `sync: false`:
   - `QLOO_API_KEY`
   - `GROQ_API_KEY`
4. **Apply**. The first build takes a few minutes: Node installs and builds the
   UI, then Python installs the API

## 3. Check it

```bash
curl https://taste-agent.onrender.com/api/health
```

Expect `"mode": "live"` and `"brain": "groq"`. If `mode` says `mock`, the Qloo
key did not reach the service; if `brain` says `rules`, the Groq key did not.

Open the same URL in a browser and the UI is there.

## Things worth knowing

**First request is slow.** Render's free plan sleeps a service after 15 minutes
of no traffic, and the next request waits ~50s for it to wake. Open the site a
minute before a demo.

**Sessions do not survive a deploy.** They are written to `DATA_DIR` (`/data`),
which lives inside the container and is replaced on every deploy. Attach a
Render Disk mounted at `/data` if you need them kept.

**Groq's free tier allows 8000 tokens per minute.** The backend reads the
remaining budget from each response and waits rather than overrunning it, but
several people using the demo at once will still feel it. The rule-based brain
answers whenever the model cannot.

**Running it locally the same way.** `npm run build` in `frontend/`, then start
the API: it picks up `frontend/dist` and serves the UI on
<http://localhost:8000> alongside the API. For day-to-day work keep using the
Vite dev server on 5173, which has hot reload and proxies `/api`.
