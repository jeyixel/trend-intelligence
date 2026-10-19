"""One entry point the UI / Module F can call: analyse(idea, domain) -> structured report (dict)."""
import config
from database import db
from ideas import llm_ideas, template_ideas
from retrieval import embedder, rank


def analyse(idea: str, domain: str, description: str = "", use_llm: bool = False) -> dict:
    query = f"{idea}. {description}".strip(". ")
    with db.connect() as con:
        topics = db.load_topics(con, domain)
        videos = db.load_reference_videos(con, domain, limit=5)
        all_topics = db.load_topics(con, None)
    matches = rank.rank_topics(query, topics, "semantic_fresh", k=config.TOP_K)
    report = {
        "idea": idea, "domain": domain,
        "backend": embedder.backend_name(),
        "sample_data": any(t["source"] == "sample_seed" for t in topics),
        "n_topics_in_domain": len(topics),
        "trending_now": rank.trending_now(topics, k=8),
        "matches": matches,
        **rank.alignment(matches),
        "ideas": template_ideas(idea, domain, matches),
        "reference_videos": videos,
        "total_topics_all_domains": len(all_topics),
    }
    if use_llm:
        report["llm_ideas"] = llm_ideas(idea, domain, matches)
    return report
