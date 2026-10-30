"""Rule-based brain.
No LLM involved: it reads the profile, decides whether to ask or recommend,
and writes the reply from templates. This is what runs when there is no
ANTHROPIC_API_KEY, and it is also the fallback if the model call fails — the
demo should never show an empty screen.
"""
import random
import re
from app.agent.base import GREETING, AgentReply, ToolCall
from app.qloo import PILLARS, get_client
from app.qloo.models import Entity
from app.qloo.service import QlooError
from app.storage.models import EntitySignal, Session
# Words that say which domain the person is asking about.
DOMAIN_WORDS: list[tuple[str, tuple[str, ...]]] = [
    ("place", ("eat", "restaurant", "cafe", "coffee", "bar", "dinner", "drink",
               "hotel", "stay", "nightlife", "brunch", "lunch")),
    # locality is searchable but Qloo rejects it as a recommendation target,
    # so travel questions resolve to places instead.
    ("place", ("travel", "trip", "visit", "city", "neighbourhood", "neighborhood",
               "holiday", "vacation", "where should i go")),
    ("movie", ("movie", "film", "watch tonight", "cinema")),
    ("tv_show", ("tv", "show", "series", "binge")),
    ("book", ("book", "read", "novel", "reading")),
    ("artist", ("music", "artist", "band", "listen", "album", "song")),
    ("brand", ("brand", "wear", "fashion", "clothes", "shop", "buy", "style")),
    ("podcast", ("podcast",)),
    ("videogame", ("game", "videogame", "play")),
]
# Narrowing tags for place results, so "where should I eat" does not return museums.
PLACE_TAGS: list[tuple[str, tuple[str, ...]]] = [
    ("urn:tag:genre:place:restaurant:cafe", ("cafe", "coffee", "brunch")),
    ("urn:tag:genre:place:restaurant:bar", ("bar", "drink", "cocktail", "nightlife", "pub")),
    ("urn:tag:genre:place:hotel", ("hotel", "stay", "sleep")),
    ("urn:tag:genre:place:restaurant", ("eat", "restaurant", "dinner", "lunch", "food", "dining")),
]


#: "in Tokyo", "around Berlin", "near Lahore"


CITY_PATTERN = re.compile(
    r"\b(?:in|around|near|visiting|to)\s+([A-Z][\w'-]+(?:\s+[A-Z][\w'-]+)?)"
)


RECOMMEND_WORDS = (
    "recommend", "suggest", "what should", "where should", "give me", "show me",
    "find me", "any ideas", "what next", "more like",
)


PILLAR_QUESTIONS = {
    "entertainment": [
        "What have you watched or listened to lately that stayed with you?",
        "Which film or show would you put on for someone you wanted to impress?",
    ],
    "lifestyle": [
        "Where do you actually like spending time — a cafe, a bar, a city you keep going back to?",
        "What does a good evening out look like for you?",
    ],
    "retail": [
        "Is there a brand whose things you keep buying, or whose shops you like being in?",
        "Whose design sense do you trust — clothes, objects, anything?",
    ],
    "culture": [
        "Whose work do you follow — a director, a writer, anyone whose name makes you pay attention?",
        "Is there someone whose taste you would borrow wholesale?",
    ],
}
# Stop words that should never be treated as the name of something.


_NOT_A_TITLE = {
    "i", "i'm", "im", "my", "me", "we", "you", "it", "this", "that", "there",
    "what", "where", "who", "how", "why", "when", "should", "would", "could",
    "like", "love", "liked", "loved", "enjoy", "enjoyed", "really", "also",
    "and", "but", "the", "a", "an", "is", "are", "was", "were", "do", "does",
    "give", "show", "find", "recommend", "suggest", "something", "anything",
    "good", "great", "nice", "best", "new", "more", "tonight", "today",
}


def detect_target_type(text: str) -> str | None:
    lowered = text.lower()
    for entity_type, words in DOMAIN_WORDS:
        if any(word in lowered for word in words):
            return entity_type
    return None



#: Words that say which kind of thing a name is, so "severance" in "that show
#: severance" is not stored as the novel Qloo ranks first.
TYPE_HINTS: list[tuple[str, tuple[str, ...]]] = [
    ("tv_show", ("show", "series", "season", "episode", "binge", "watching")),
    ("movie", ("film", "movie", "cinema")),
    ("book", ("book", "novel", "read", "reading")),
    ("author", ("author", "writer", "wrote", "novelist")),
    ("artist", ("band", "album", "song", "music", "listening", "listen")),
    ("brand", ("brand", "shop", "store", "wear", "wearing", "label")),
    ("videogame", ("game", "gaming", "playing")),
    ("place", ("cafe", "coffee", "bar", "restaurant", "hotel", "spot", "place")),
    ("podcast", ("podcast",)),
    ("person", ("director", "filmmaker", "designer", "architect", "actor")),
]


def detect_type_hint(text: str) -> str | None:
    lowered = text.lower()
    for entity_type, words in TYPE_HINTS:
        if any(re.search(rf"\b{re.escape(word)}", lowered) for word in words):
            return entity_type
    return None


def detect_place_tags(text: str) -> list[str]:
    lowered = text.lower()
    for tag_id, words in PLACE_TAGS:
        if any(word in lowered for word in words):
            return [tag_id]
    return []


def detect_location(text: str) -> str | None:
    match = CITY_PATTERN.search(text)
    return match.group(1).strip() if match else None


def wants_recommendation(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in RECOMMEND_WORDS) or lowered.strip().endswith("?")


#: "i love muji and acne studios", "into radiohead", "severance is my favourite"
_LIKE_LEAD = re.compile(
    r"\b(?:i\s+)?(?:really\s+)?(?:like|love|enjoy|adore|into|dig|prefer|favou?rite\s+is)\s+(.+)",
    re.IGNORECASE,
)
_SPLIT = re.compile(r"\s*(?:,|\band\b|\balso\b|&|/)\s*", re.IGNORECASE)
_TRAILING = re.compile(
    r"\s+(?:is|are|was|were)\s+my\s+(?:favou?rite|top|go[- ]?to).*$|\s+is\s+my\s+kind\s+of.*$",
    re.IGNORECASE,
)


def _clean(phrase: str) -> str:
    phrase = _TRAILING.sub("", phrase).strip(" .!?,;:")
    words = [w for w in phrase.split() if w.lower() not in _NOT_A_TITLE]
    return " ".join(words).strip()


def extract_candidates(text: str) -> list[str]:
    """Pull out things that look like titles or names.

    Quoted text wins, then capitalised runs ("Blade Runner 2049"). People type
    lower case too, so anything after "I like ..." is also treated as a name -
    Qloo and the match guard decide whether it is real.
    """
    quoted = re.findall(r"[\"'“‘]([^\"'”’]{2,60})[\"'”’]", text)
    if quoted:
        return [q.strip() for q in quoted][:3]

    candidates: list[str] = []
    for match in re.finditer(r"\b([A-Z][\w'&-]*(?:\s+(?:[A-Z][\w'&-]*|\d{2,4}))*)", text):
        phrase = match.group(1).strip()
        if phrase.lower() in _NOT_A_TITLE or len(phrase) < 3:
            continue
        candidates.append(phrase)

    lead = _LIKE_LEAD.search(text)
    if lead:
        for part in _SPLIT.split(lead.group(1)):
            phrase = _clean(part)
            if len(phrase) < 3 or _is_intent_phrase(phrase):
                continue
            if not any(phrase.lower() == c.lower() for c in candidates):
                candidates.append(phrase)

    if not candidates:
        stripped = _clean(text)
        words = stripped.split()
        # A bare short answer ("severance") is almost certainly a title.
        if 1 <= len(words) <= 4 and not wants_recommendation(text):
            candidates.append(stripped)

    return [c for c in candidates if c][:3]


#: Every intent word, so "somewhere for coffee instead" is never read as a title.


_INTENT_WORDS = {
    word
    for _, words in DOMAIN_WORDS
    for phrase in words
    for word in phrase.split()
} | {word for phrase in RECOMMEND_WORDS for word in phrase.split()}


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _is_intent_phrase(candidate: str) -> bool:
    words = _tokens(candidate)
    return bool(words) and words <= (_INTENT_WORDS | _NOT_A_TITLE)


def plausible_match(query: str, name: str) -> bool:
    """Qloo always returns its best guess, and for a phrase like "somewhere for
    coffee" that guess is junk. Only trust a hit that shares most of the query."""
    asked = _tokens(query)
    if not asked:
        return False
    return len(asked & _tokens(name)) / len(asked) >= 0.6


#: Qloo ranks a brand well above its shops (Muji: 0.98 vs 0.76), but a book and
#: a show of the same name sit on top of each other (Severance: 0.996 vs 0.993).
#: Only that second case is a real coin flip.
AMBIGUOUS_GAP = 0.01


def _is_ambiguous(query: str, matches: list[Entity]) -> bool:
    """True when the two best hits are the same name, different kinds of thing,
    and Qloo cannot separate them."""
    exact = [
        m for m in matches
        if m.name.lower().strip() == query.lower().strip() and m.popularity is not None
    ]
    if len(exact) < 2:
        return False

    best, runner_up = exact[0], exact[1]
    if best.type == runner_up.type:
        return False
    return abs(best.popularity - runner_up.popularity) < AMBIGUOUS_GAP


def _reason(recommendation: Entity, signal_names: list[str]) -> str:
    shared: list[str] = []
    for tag in recommendation.tags:
        name = tag.name.lower()
        if name not in shared:
            shared.append(name)
        if len(shared) == 3:
            break
    names = " and ".join(signal_names[:2]) if signal_names else "your profile"
    if shared:
        return f"Follows {names} on {', '.join(shared)}."
    return f"Close to {names} in Qloo's taste graph."


def _thinnest_pillar(session: Session) -> str | None:
    coverage = session.profile.pillar_coverage()
    missing = [key for key, count in coverage.items() if count == 0]
    if not missing:
        return None
    # Rotate rather than hammering the same pillar every turn.
    fresh = [key for key in missing if key != session.last_asked_pillar]
    return (fresh or missing)[0]


async def resolve_mentions(session: Session, text: str) -> list[EntitySignal]:
    """Turn names in the message into stored taste signals."""
    client = get_client()
    known = {s.id for s in session.profile.entities}
    added: list[EntitySignal] = []
    city = detect_location(text)
    hint = detect_type_hint(text)
    for candidate in extract_candidates(text):
        if city and candidate.lower() == city.lower():
            continue
        if _is_intent_phrase(candidate):
            continue
        try:
            matches = await client.search(candidate, entity_type=hint, take=5)
        except QlooError:
            break

        # Qloo also returns types we have no pillar for (albums, videos). A
        # signal we cannot place is worse than no signal, so skip those.
        placeable = [m for m in matches if m.id and m.pillar]
        if not placeable:
            continue
        if hint is None and _is_ambiguous(candidate, placeable):
            # Same name, different kinds of thing, and nothing in the sentence
            # says which. Guessing writes the wrong taste into the profile, so
            # leave it for the agent to pin down with a type.
            continue
        entity = placeable[0]
        if entity.id in known or not plausible_match(candidate, entity.name):
            continue
        signal = EntitySignal.from_entity(entity)
        session.profile.entities.append(signal)
        known.add(entity.id)
        added.append(signal)
    return added


async def respond(session: Session, text: str) -> AgentReply:
    new_signals = await resolve_mentions(session, text)
    city = detect_location(text)
    if city:
        session.profile.location = city
    profile = session.profile
    liked = profile.liked_entity_ids()
    tool_calls: list[ToolCall] = []
    if not liked:
        return AgentReply(
            message=GREETING if not text.strip() else
            "I could not place that one. Give me a film, show, artist, brand or "
            "place by name and I will start from there.",
            new_signals=new_signals,
        )
    signal_names = [s.name for s in profile.entities if s.sentiment == "like"][-2:]
    target_type = detect_target_type(text)
    missing_pillar = _thinnest_pillar(session)
    # Ask rather than guess while the profile is still thin and nothing was requested.
    if target_type is None and missing_pillar and len(liked) < 4 and not wants_recommendation(text):
        question = random.choice(PILLAR_QUESTIONS[missing_pillar])
        opener = (
            f"Got it — {signal_names[-1]} is in." if new_signals
            else "Noted."
        )
        session.last_asked_pillar = missing_pillar
        return AgentReply(
            message=f"{opener} {question}",
            new_signals=new_signals,
            asked_about=missing_pillar,
        )
    # Otherwise recommend. Default to the pillar we know least about.
    if target_type is None:
        target_type = {
            "entertainment": "movie",
            "lifestyle": "place",
            "retail": "brand",
            "culture": "person",
        }.get(missing_pillar or "", "place")
    if target_type in ("place", "locality") and not session.profile.location:
        session.last_asked_pillar = "lifestyle"
        return AgentReply(
            message="Happy to — which city are you in, or heading to? Qloo anchors "
                    "places geographically, so I would rather not guess.",
            new_signals=new_signals,
            asked_about="lifestyle",
        )
    exclude = session.shown_entity_ids + profile.disliked_entity_ids() + liked
    place_tags = detect_place_tags(text) if target_type in ("place", "locality") else []
    location = session.profile.location if target_type in ("place", "locality") else None
    try:
        results = await get_client().insights(
            target_type,
            signal_entities=liked,
            signal_tags=profile.liked_tag_ids(),
            location=location,
            filter_tags=place_tags,
            take=24,
        )
    except QlooError as exc:
        return AgentReply(
            message=f"Qloo did not answer just then ({exc}). Try again in a moment.",
            new_signals=new_signals,
        )
    blocked = set(exclude)
    picks: list[Entity] = []
    seen: set[str] = set()
    for entity in results:
        if entity.id in blocked or entity.id in seen:
            continue
        seen.add(entity.id)
        picks.append(entity)
        if len(picks) >= 4:
            break
    tool_calls.append(
        ToolCall(
            name="get_recommendations",
            arguments={"target_type": target_type, "entity_ids": liked},
            result_summary=f"{len(picks)} picks after filtering",
        )
    )
    if not picks:
        return AgentReply(
            message="I have shown you everything Qloo has there. Try another domain, "
                    "or add one more thing you like.",
            new_signals=new_signals,
            tool_calls=tool_calls,
        )
    session.remember_shown([p.id for p in picks])
    label = PILLARS.get(picks[0].pillar or "", {}).get("label", "these")
    because = " and ".join(signal_names) if signal_names else "your profile"
    lines = [f"Going on {because}, here is where your taste points in {label.lower()}:", ""]
    for pick in picks:
        lines.append(f"**{pick.name}** — {_reason(pick, signal_names)}")
    follow_up = _thinnest_pillar(session)
    if follow_up:
        session.last_asked_pillar = follow_up
        lines.append("")
        lines.append(random.choice(PILLAR_QUESTIONS[follow_up]))
    return AgentReply(
        message="\n".join(lines),
        recommendations=picks,
        new_signals=new_signals,
        asked_about=follow_up,
        tool_calls=tool_calls,
    )
