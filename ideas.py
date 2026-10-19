"""Evidence-grounded content-idea generator.
Default: template angles per domain filled with *retrieved* topics (never invents a trend).
Optional: LLM rewrite restricted to the same evidence (needs ANTHROPIC_API_KEY)."""
import json

import config

TEMPLATES = {
    "Gaming": [
        ("Challenge twist", "Turn “{base}” into a challenge episode inspired by “{topic}” (time limit, hardcore rules or a ‘can I survive…?’ hook)."),
        ("Beginner / local angle", "Make a beginner-friendly, Sri Lanka-context version: explain “{topic}” for new players using “{base}” as the example."),
        ("Versus format", "Build a comparison or ‘versus’ video around “{topic}”, with “{base}” as the main case."),
    ],
    "Education": [
        ("Step-by-step explainer", "Create a step-by-step explainer linking “{base}” to “{topic}”, with a downloadable summary sheet."),
        ("Common mistakes", "Cover the common student mistakes around “{topic}”, using “{base}” as the worked example."),
        ("60-second revision", "Publish a short 60-second revision cut of “{base}” riding the interest in “{topic}”."),
    ],
    "Cooking": [
        ("Budget / home version", "Do a budget, at-home version of “{base}” with the angle “{topic}” and a cost-per-serving breakdown."),
        ("Quick twist", "Put a twist on “{base}” inspired by “{topic}” (e.g. 15-minute or air-fryer version)."),
        ("Street vs home", "Compare the street-food version and the home version for “{topic}”, starting from “{base}”."),
    ],
}
GENERIC = [("Trend tie-in", "Connect “{base}” to the current interest in “{topic}” in the first 30 seconds of the video.")]


def _evidence(m: dict) -> dict:
    return {"topic": m["topic_text"], "source": m["source"], "source_url": m.get("source_url"),
            "last_seen_at": m["last_seen_at"], "first_seen_at": m["first_seen_at"],
            "lifecycle": m["lifecycle"], "days_ago": round(m["age_days"], 1)}


def template_ideas(base_idea: str, domain: str, matches: list[dict], n: int = 3) -> list[dict]:
    templates = TEMPLATES.get(domain, GENERIC)
    out = []
    for i, m in enumerate(matches[:n]):
        name, tpl = templates[i % len(templates)]
        out.append({
            "angle": name,
            "suggestion": tpl.format(base=base_idea, topic=m["topic_text"]),
            "why": (f"“{m['topic_text']}” was last seen {m['age_days']:.0f} day(s) ago via {m['source']} "
                    f"(status: {m['lifecycle']}; match score {m['score']:.2f})."),
            "evidence": _evidence(m),
        })
    return out


def llm_ideas(base_idea: str, domain: str, matches: list[dict], n: int = 3):
    """Optional: let an LLM phrase the ideas, but ONLY from the evidence we retrieved."""
    if not config.ANTHROPIC_API_KEY:
        return None
    try:
        import anthropic
    except ImportError:
        return None
    evidence = [_evidence(m) for m in matches[:5]]
    prompt = (
        f"A Sri Lankan YouTube creator plans a {domain} video: \"{base_idea}\".\n"
        f"Retrieved, dated trend evidence (JSON):\n{json.dumps(evidence, ensure_ascii=False)}\n\n"
        f"Write {n} specific video angles. Rules: use ONLY the evidence above; never claim a topic is "
        "'rising' or 'viral' unless its lifecycle is 'new' or 'sustained'; cite the topic text each angle "
        "relies on; if evidence is weak, say so. Return JSON list of {angle, suggestion, based_on_topic}."
    )
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = client.messages.create(model=config.LLM_MODEL, max_tokens=800,
                                 messages=[{"role": "user", "content": prompt}])
    try:
        text = msg.content[0].text.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(text)
    except Exception:
        return None
