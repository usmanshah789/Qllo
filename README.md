# Taste Agent

A conversational agent that learns what you like and follows your taste into
other domains — a film leads to a café, a brand, a city, a writer.

All taste data comes from the [Qloo](https://qloo.com) Insights API. The model
never invents a recommendation: every card on screen is an entity Qloo returned.

## What it does

You name things you love. The agent resolves each one to a real Qloo entity,
builds a taste profile, and asks about the domains it knows nothing about. When
you ask for something, it queries Qloo across domains and explains each pick
using the tags Qloo actually returned.

- **Cross-domain** — *Blade Runner 2049* → Tokyo cafés, Tesla, Radiohead
- **Four pillars** — Entertainment, Lifestyle & Travel, Fashion & Brands,
  People & Culture, covering all 13 Qloo entity types
- **Taste read** — the tags that recur across everything you like, counted
  rather than generated
- **Location aware** — Qloo anchors places geographically, so "where should I
  eat" in Lahore returns Lahore
- **Remembers** — each conversation is a session on disk; likes, dislikes and
  location persist

## Running it

Needs Python 3.12+ and Node 20+.

```bash
# backend
cd backend
python -m venv ../.venv && ../.venv/Scripts/pip install -r requirements.txt
../.venv/Scripts/python -m uvicorn app.main:app --port 8000

# frontend, in a second terminal
cd frontend
npm install && npm run dev
```

Then open http://localhost:5173.

Copy `.env.example` to `.env` and fill in:

| Variable | Needed for |
|---|---|
| `QLOO_API_KEY` | live Qloo data (blank → mock mode) |
| `GROQ_API_KEY` | the LLM brain (blank → rule-based brain) |
| `ANTHROPIC_API_KEY` | use Claude instead of Groq |

Nothing is mandatory. With no keys at all the app still runs on mock data and a
rule-based planner — useful when the network is unreliable during a demo.

## How it is put together

```
backend/app/
  qloo/        client, mock client, normalized models, the 13 types / 4 pillars
  agent/       tools, Groq brain, Claude brain, rule-based planner, taste read
  storage/     one JSON file per session, written atomically
  routers/     /api/chat, /api/sessions, /api/qloo
frontend/src/  React UI, five themes, chat + taste profile panel
docs/          what the live Qloo API actually does, probed rather than assumed
```

Three brains share one set of tools and one prompt:

```
ANTHROPIC_API_KEY set?  → Claude
else GROQ_API_KEY set?  → Groq
else                    → rule-based planner
```

If the model call fails mid-conversation the planner answers instead, so the UI
never shows an error page.

## Notes on the Qloo API

Probed against the live hackathon API, not taken from docs:

- `/search` returns a flat list; `/v2/insights` nests under `results.entities`;
  `/v2/analysis/compare` answers with **tags**, not entities
- Entity type lives in `types[]` on search results but in `subtype` on insights
  results, where `type` is the useless string `"urn:entity"`
- `director` is rejected by both endpoints; `author` and `locality` are
  searchable but not valid recommendation targets; `actor` searches return
  nothing and carry no images
- Most tags are Wikipedia bookkeeping ("2003 establishments in California"), so
  only the descriptive families are kept

Full notes in [docs/qloo-live-samples.md](docs/qloo-live-samples.md), and the
build log with every bug found along the way in [PROGRESS.md](PROGRESS.md).

## Deploying

[`render.yaml`](render.yaml) defines both services. See
[DEPLOY.md](DEPLOY.md) for the steps.

Sessions are written to the API service's own disk, which Render wipes on every
deploy. That is fine for a demo; attach a Render Disk to keep them.
