# Qloo Taste Agent — Progress

## Stage 1 — Foundation ✅
- `backend/` — FastAPI app, `/api/health` endpoint
- `backend/app/config.py` — reads `.env`, auto mock/live switch
- `frontend/` — React (Vite) + Tailwind v4, `/api` proxied to backend
- `.env` / `.env.example` — Qloo + LLM keys (abhi khali)
- `data/sessions/` — JSON storage ke liye (Stage 3)

Test: frontend par Backend `ok`, mode `mock` dikhta hai.


## Stage 2 - Qloo Layer (mock + live) [DONE]
- `backend/app/qloo/entity_types.py` - 13 Qloo entity types, 4 pillars mein baante
- `backend/app/qloo/models.py` - Entity / Tag normalized shape (mock aur live dono isi mein aate hain)
- `backend/app/qloo/client.py` - asli Qloo API (endpoints harness ke --dry-run se liye)
- `backend/app/qloo/mock.py` - 26 entity ka seeded catalog, deterministic ranking
- `backend/app/qloo/service.py` - key hai ya nahi, uske hisaab se client chunta hai
- `backend/app/routers/qloo.py` - /api/qloo/{types,search,tags,insights,compare}
- `docs/qloo-cli-schema.json`, `docs/qloo-entity-types.json` - harness se nikala reference

Asli endpoints jo pata chale:
    GET /search               query, types, take
    GET /v2/insights          filter.type, signal.interests.entities, signal.interests.tags
    GET /entities             entity_ids
    GET /v2/analysis/compare  a.signal.interests.entities, b..., filter.type

### Stage 2b - LIVE par switch [DONE]
- Asli hackathon key .env mein daal di -> app khud `live` mode par chala gaya
- Paanchon endpoints asli API par verify kiye (docs/qloo-live-samples.md)
- Fix: insights results mein type `urn:entity` hota hai, asli type `subtype` mein -> pillar None aa raha tha
- Fix: compare `take` ignore karta hai -> client side trim
- Fix: compare entities nahi, scored TAGS deta hai -> return type badla
- Fix: short_descriptions se chhoti summary li, lambe paragraph ki jagah
- Mock mode abhi bhi kaam karta hai (QLOO_MOCK_MODE=1 se test kiya)

Live check: Inception -> Tesla/Apple (brands), Radiohead/Thom Yorke (artists)

## Stage 3 - Session Storage [DONE]
- `backend/app/storage/models.py` - Session, TasteProfile, EntitySignal, TagSignal, Message
- `backend/app/storage/store.py` - JSON file per session, atomic write (tmp + rename), thread lock
- `backend/app/routers/sessions.py` - /api/sessions CRUD + signals + tags + messages
- Signal add karte waqt Qloo se resolve hota hai -> asli entity_id, type aur pillar store hota hai
- Dobara wahi cheez add karo to duplicate nahi banti, sentiment update ho jata hai
- `pillar_coverage()` batata hai kaunsa pillar abhi khali hai (agent isi se sawal poochega)
- Dislike alag se store hota hai, coverage mein count nahi hota

Test: 4 signals (Inception/Severance/MUJI/Murakami) -> coverage
{entertainment:1, lifestyle:0, retail:1, culture:1}, missing: lifestyle

## Stage 4 - Agent Brain [DONE]
- `backend/app/agent/tools.py` - 4 Qloo tools + Claude ke liye JSON schemas
  (search_entity, get_recommendations, find_tags, compare_tastes)
- `backend/app/agent/planner.py` - rule-based brain, bina LLM ke poora chalta hai
- `backend/app/agent/brain.py` - Claude tool-use loop (claude-opus-5)
- `backend/app/agent/__init__.py` - brain chunta hai; Claude fail ho to planner le leta hai
- `backend/app/routers/chat.py` - POST /api/chat (UI sirf isi se baat karegi)

Stage 4 mein jo asli bugs mile aur theek kiye:
1. Tags kuda the - "2003 establishments in California" type wikipedia_category.
   Ab filter hai: aesthetic_property/emotional_tone/style/genre pehle,
   wikipedia_category bilkul nikal diya. Natija: "minimalist design, sleek surfaces"
2. "Where should I eat" par New York ke landmarks aate the (Qloo filming location
   ko weight deta hai). Ab filter.location.query + place genre tags lagte hain.
   Natija: Tokyo maanga to Tokyo ke restaurants aate hain, Lahore bhi chalta hai.
3. "somewhere for coffee instead" ko entity samajh kar Qloo mein dhoonda aur
   junk entry profile mein ghus gayi. Ab intent-phrase guard + match guard hai
   (query aur result ke tokens 60% match hone chahiyein).
4. Har baar wahi pillar ka sawal repeat ho raha tha -> last_asked_pillar rotate karta hai

Design:
- Dono brains ek hi tools use karte hain, isliye behaviour same rehta hai
- Claude ko mana hai ke apni taraf se recommend kare - sirf Qloo ka data
- UI cards us data se bante hain jo Qloo ne wapas kiya, model ki prose se nahi
- Galat LLM key par test kiya: 401 aaya, planner ne jawab de diya, user ko error nahi dikha

### Stage 4b - Groq support [DONE]
- `backend/app/agent/prompt.py` - system prompt + profile block, dono brains share karte hain
- `backend/app/agent/groq_brain.py` - Groq (OpenAI-compatible) tool-calling loop
- `backend/app/agent/signals.py` - LLM jo lookup kare wo profile mein save hota hai
- config: ANTHROPIC key ho to Claude, warna GROQ key ho to Groq, warna rules
- Model: openai/gpt-oss-120b (is account par llama models nahi hain)

Jo masle aaye aur fix kiye:
1. .env ki key kaam nahi kar rahi thi - system environment mein ek PURANI
   GROQ_API_KEY pari thi jo .env ko dabaa rahi thi. load_dotenv(override=True)
2. Groq free tier = 8000 tokens/min. Sab chhota kiya: tool schemas 429 tokens,
   system prompt 318, tool results 1400 chars, history 6 messages, max_tokens 600
   + 429 par ek retry with backoff, phir planner fallback
3. LLM brains profile mein kuch save hi nahi kar rahe the - sirf planner karta tha.
   Ab har lookup signal ban jata hai (agar user ne khud naam liya ho)
4. Model ka recommendation-search ("futuristic restaurant Tokyo") bhi signal ban
   raha tha - ab check hota hai ke user ne apne words mein kaha tha ya nahi
5. Tool loop turns khatam ho jate the to jawab khali aata tha - ab aakhir mein
   ek bar bina tools ke poocha jata hai taake prose mile
6. Qloo "Apple Inc" kehta hai, model "Apple" likhta hai -> card nahi banta tha.
   Ab corporate suffix hata kar match hota hai
7. Location sirf planner parhta tha -> ab orchestrator har message par parhta hai

## Stage 5 + 6 - API aur UI [DONE]
- `/api/chat` hi wo ek endpoint hai jo UI use karti hai (Stage 5 isi mein aa gaya)
- `frontend/src/api.js` - fetch wrapper, ApiError status ke sath
- `frontend/src/App.jsx` - session state, localStorage, optimistic user message
- `components/` - Header, Welcome, Message, EntityCard, Composer, ProfilePanel
- `lib/richText.jsx` - halka markdown (bold + list), `lib/pillars.js` - 4 pillars

UI mein kya hai:
- Chat thread, bold names, Enter se send (Shift+Enter nayi line)
- Recommendation cards: image, type, match %, address, tags
- Sidebar: taste profile (hata bhi sakte hain), 4 pillars ka coverage, location
- Header badges: Qloo live/mock aur kaunsa brain chal raha hai

Browser mein test karte waqt jo bugs mile:
1. Backend restart par frontend ne localStorage saaf kar diya tha -> session gaya.
   Ab sirf 404 par saaf hota hai, network error par nahi
2. richText ka global regex paragraphs ke beech lastIndex yaad rakh raha tha ->
   bold toot raha tha. Ab har call par naya regex
3. Model kabhi ***name*** jaisa toota markdown likhta hai -> ab normalize hota hai
4. Qloo places ka `disambiguation` poora address hota hai -> card par naam
   dhakel raha tha. Ab sirf chhota subtitle (<=18 chars) dikhta hai
5. Groq ko finaliser call mein tools band kiye the -> 400 tool_use_failed.
   Ab tools on rehte hain, sirf prose maanga jata hai
6. Tool loop turns khatam -> ab 7 turns, aur phir bhi khali ho to planner le leta hai
7. Model `search_entity` se recommendations dhoond raha tha (taste match nahi hota).
   Prompt sakht kiya + places ke liye `category` (cafe/bar/restaurant/hotel) diya
8. Sabse bara: pehle turn par koi signal record nahi hota tha, isliye model har
   baar dobara search karta aur turns/tokens zaya hote. Ab message parsing har
   brain ke liye chalti hai -> pehla turn 0 tool calls, doosra turn 1 call

## Stage 7 - Pillars + Polish [DONE]
- `backend/app/agent/taste_read.py` - taste signature: har liked entity ke poore
  tags Qloo se lete hain aur jo recur karte hain wo dikhate hain. Koi model
  nahi likhta - tag ya to unki entities par hai ya nahi hai
- `GET /api/sessions/{id}/taste-read` - signature + kitni entities se bana
- `POST /api/sessions/{id}/signals/{entity_id}/dislike` - card par x dabao,
  wo cheez dobara kabhi nahi aayegi (recommendations se exclude hoti hai)
- `frontend/src/components/TasteRead.jsx` - sidebar mein signature chips
- Pillars ab clickable hain - har pillar ka apna sawal bhejta hai (cross-domain jump)
- Mobile: sidebar ke liye drawer (Profile button), header phone par fit hota hai

Stage 7 mein jo theek kiya:
1. Taste signature pehle bekaar tha - sab tags 1x the. Wajah: har entity ke tags
   16 par cut ho rahe the, to overlap kho jata tha. Ab 40 tak rakhte hain aur
   jo 2+ entities par aaye usay pehle dikhate hain
   Natija: Severance + Blade Runner + MUJI + Murakami ->
   "Isolation, Fiction, Dystopian, Thoughtful"
2. Qloo aise entity types bhi deta hai jo hamare 4 pillars mein nahi aate
   (album, video). Aise signals store hi nahi hote ab - jo rakh nahi sakte
   usay rakhna na rakhne se bura hai

Known limitation:
- "Severance" Qloo par Book (0.996) TV Show (0.993) se upar hai, isliye parser
  book pakarta hai. LLM brain type hint ke sath search kare to theek hota hai.
  User sidebar se signal hata sakta hai.


## Qloo API ki haqeeqat (live probe se)

Qloo 13 entity types list karta hai lekin hackathon API sab ko har jagah
qubool nahi karta. Maine har type dono endpoints par probe kiya:

| type | /search | /v2/insights |
|---|---|---|
| movie, tv_show, book, brand, artist, person, videogame, podcast, place | ok | ok |
| actor | 0 results | ok lekin koi image nahi |
| director | 0 results | error |
| author | ok | error |
| locality | ok | error |

Isliye `entity_types.py` mein SEARCHABLE aur RECOMMENDABLE alag hain:
- agent ko sirf wahi types offer hote hain jo us call par chalte hain
- director/actor search karte waqt person ban jate hain
- planner ka culture default `director` tha -> ab `person`
  (yani culture recommendations pehle chup chaap fail ho rahe the)
- travel ka default `locality` tha -> ab `place`
- actor target se hata diya (person behtar hai: searchable + images)

Images: movie, tv_show, book, brand, artist, person, podcast, place par
har result pe aati hain. videogame par kuch pe. actor par bilkul nahi.

## Teen baaki masle theek kiye

1. Chhote akhar wale naam ab chalte hain. Pehle parser sirf capital letters se
   naam pehchanta tha, "i love muji" kuch nahi karta tha. Ab "i like/love/into..."
   ke baad jo aaye usay bhi naam maana jata hai, aur comma/and par tootta hai.
2. Severance wali ambiguity. Qloo par book (0.9961) show (0.9932) se upar hai.
   Ab do cheezein hoti hain:
   - jumle se type ka ishara ("show severance" -> tv_show, "novel" -> book)
   - ishara na ho aur dono hits ka farq 0.01 se kam ho to parser kuch store
     nahi karta, LLM type hint ke sath khud pin karta hai (test mein TV Show nikla)
   Muji par yeh trigger nahi hota kyunke Brand 0.98 vs Place 0.76 ka farq bara hai.
3. Groq rate limit. Ab har jawab ke headers se remaining tokens parhte hain aur
   budget kam ho to pehle se rukte hain; ek waqt mein ek hi call jati hai.
   Test: 6 messages lagataar, 68 second, saare groq ne diye, ek bhi 429 nahi.

## Frontend redesign

Mockup ke mutabiq: aurora background, 5 themes, gradient accents.

- `frontend/src/lib/themes.js` + `index.css` - 5 palettes (Aurora, Candy,
  Sunset, Jade, Royal). Har theme sirf do accent hues badalta hai, greys wahi
  rehte hain taake text contrast kabhi na gire. Choice localStorage mein.
- `.aurora` background: fixed radial glows + dot grid, scroll ke sath hilta nahi
- Header: gradient logo, theme switcher, badges, accent hairline
- User bubble gradient, agent reply panel (blur + border)
- Sidebar labels ke neeche chhota gradient rule

Apni taraf se jo daala:
- `link` field - Qloo ke external data se asli link banta hai:
  website (places) > IMDb > Letterboxd > Google Maps > Instagram
  Card ka naam ab clickable hai
- `rating` field - IMDb user_rating (8.7/10) ya Tripadvisor (4.5/5).
  Yeh Qloo ki affinity se alag cheez hai - asli public rating
- Affinity ab number ke sath ek gradient bar bhi hai
- "Copy my taste read" button - taste signature clipboard par

Bug jo redesign ke dauran mila:
- Auto-scroll toot gaya tha. bottomRef.scrollIntoView() us ancestor ko scroll
  karta hai jo usay scrollable lage; naye layout mein wo thread nahi tha.
  Ab thread container ka scrollTo() seedha use hota hai.
