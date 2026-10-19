"""Streamlit prototype UI:  streamlit run app.py"""
import pandas as pd
import streamlit as st

import config
import service
from database import db

st.set_page_config(page_title="Trend Intelligence (Module B)", page_icon="📈", layout="wide")
st.title("📈 Trend Intelligence Engine — Module B")
st.caption("What's trending for Sri Lankan creators, is my idea relevant, and how can I use it?")

with db.connect() as con:
    n_topics = con.execute("SELECT COUNT(*) FROM topics").fetchone()[0]
    last_run = con.execute("SELECT MAX(collected_at) FROM topic_observations").fetchone()[0]

with st.sidebar:
    st.header("Data status")
    st.write(f"Topics stored: **{n_topics}**")
    st.write(f"Last collection: **{last_run or 'never'}**")
    st.caption("Run `python collect.py` (live) or `python collect.py --seed` (sample demo data).")
    use_llm = st.checkbox("LLM-written angles (needs ANTHROPIC_API_KEY)", value=False)

if n_topics == 0:
    st.warning("Database is empty. Run `python collect.py --seed` for demo data, or `python collect.py` for live data.")
    st.stop()

c1, c2 = st.columns([1, 3])
domain = c1.selectbox("Domain", config.DOMAINS)
idea = c2.text_input("Your video idea / title", "Minecraft Survival Episode 1")
desc = st.text_area("Optional description", "", height=70)

if st.button("Analyse trends", type="primary") and idea.strip():
    r = service.analyse(idea, domain, desc, use_llm=use_llm)
    if r["sample_data"]:
        st.warning("⚠️ Includes SAMPLE seed topics — illustrative demo data, not live trend results.")
    st.caption(f"Similarity backend: {r['backend']}")

    m1, m2, m3 = st.columns(3)
    m1.metric("Trend alignment (0–1)", r["trend_alignment"], help="Heuristic: mean score of top-3 matches. Uncalibrated.")
    m2.metric("Verdict", r["label"])
    m3.metric("Topics in this domain", r["n_topics_in_domain"])

    st.subheader("💡 Suggested content angles")
    if not r["ideas"]:
        st.info("No sufficiently related topics found — try a more descriptive idea or add topics via CSV.")
    for i in r["ideas"]:
        with st.container(border=True):
            st.markdown(f"**{i['angle']}** — {i['suggestion']}")
            ev = i["evidence"]
            link = f" · [source]({ev['source_url']})" if ev.get("source_url") else ""
            st.caption(f"Evidence: {i['why']}{link}")
    if r.get("llm_ideas"):
        st.subheader("🤖 LLM-written angles (grounded in the evidence above)")
        st.json(r["llm_ideas"])

    st.subheader("🔎 Most relevant topics")
    st.dataframe(pd.DataFrame([{
        "topic": m["topic_text"], "score": round(m["score"], 3), "similarity": round(m["similarity"], 3),
        "freshness": round(m["freshness"], 3), "status": m["lifecycle"],
        "last seen (days ago)": round(m["age_days"], 1), "source": m["source"]} for m in r["matches"]]),
        width='stretch', hide_index=True)

    st.subheader(f"🔥 Trending now in {domain}")
    st.dataframe(pd.DataFrame([{
        "topic": t["topic_text"], "trend score": round(t["trend_score"], 3), "status": t["lifecycle"],
        "days observed": t["n_days"], "last seen (days ago)": round(t["age_days"], 1), "source": t["source"]}
        for t in r["trending_now"]]), width='stretch', hide_index=True)

    if r["reference_videos"]:
        st.subheader("🎬 Reference videos (YouTube, original metadata — not used in scoring)")
        for v in r["reference_videos"]:
            st.markdown(f"- [{v['title']}]({v['source_url']}) — {v['channel_title']} · {v['published_at'][:10]}")
