"""One entry point the UI / Module F can call: analyse(idea, domain) -> structured report (dict)."""
import time

import config
from analysis_logging import LOGGER
from database import db
from ideas import llm_ideas, template_ideas
from retrieval import embedder, rank


def analyse(idea: str, domain: str, description: str = "", use_llm: bool = False) -> dict:
    started = time.perf_counter()
    query = f"{idea}. {description}".strip(". ")
    stage = "load_data"
    if config.TREND_ANALYSIS_LOGS:
        LOGGER.info("analysis.start idea=%r domain=%r description_provided=%s",
                    idea, domain, bool(description.strip()))
    try:
        with db.connect() as con:
            topics = db.load_topics(con, domain)
            videos = db.load_reference_videos(con, domain, limit=5)
            all_topics = db.load_topics(con, None)
        if config.TREND_ANALYSIS_LOGS:
            LOGGER.info("analysis.data_loaded domain=%r topics=%d reference_videos=%d all_topics=%d",
                        domain, len(topics), len(videos), len(all_topics))

        stage = "retrieve_and_rank"
        matches = rank.rank_topics(
            query, topics, "semantic_fresh", k=config.TOP_K,
            log_candidates=config.TREND_ANALYSIS_LOGS,
        )
        backend = embedder.backend_name()
        if config.TREND_ANALYSIS_LOGS:
            LOGGER.info("analysis.retrieval_complete backend=%s candidates=%d returned_matches=%d",
                        backend, len(topics), len(matches))

        stage = "build_report"
        report = {
            "idea": idea, "domain": domain,
            "backend": backend,
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
            stage = "llm_ideas"
            if config.TREND_ANALYSIS_LOGS:
                LOGGER.info("analysis.llm_started")
            report["llm_ideas"] = llm_ideas(idea, domain, matches)
            if config.TREND_ANALYSIS_LOGS:
                LOGGER.info("analysis.llm_complete ideas_returned=%s",
                            bool(report["llm_ideas"]))

        if config.TREND_ANALYSIS_LOGS:
            LOGGER.info(
                "analysis.complete alignment=%.3f label=%r matches=%d ideas=%d "
                "reference_videos=%d elapsed_ms=%.1f",
                report["trend_alignment"], report["label"], len(matches), len(report["ideas"]),
                len(videos), (time.perf_counter() - started) * 1000,
            )
        return report
    except Exception as exc:
        if config.TREND_ANALYSIS_LOGS:
            LOGGER.exception("analysis.failed stage=%s error_type=%s elapsed_ms=%.1f",
                             stage, type(exc).__name__, (time.perf_counter() - started) * 1000)
        raise
