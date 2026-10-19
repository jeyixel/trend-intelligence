"""Command-line demo:  python demo.py "Minecraft Survival Episode 1" Gaming"""
import sys

import service

idea = sys.argv[1] if len(sys.argv) > 1 else "Minecraft Survival Episode 1"
domain = sys.argv[2] if len(sys.argv) > 2 else "Gaming"
r = service.analyse(idea, domain)

print(f"\nIDEA: {r['idea']}   DOMAIN: {r['domain']}   (similarity backend: {r['backend']})")
if r["sample_data"]:
    print("!! Some topics come from SAMPLE seed data, not live collection !!")
print(f"\nTREND ALIGNMENT: {r['trend_alignment']}  -> {r['label']}")
print("\nTRENDING NOW in this domain:")
for t in r["trending_now"][:5]:
    print(f"  - {t['topic_text']:<45} [{t['lifecycle']}, last seen {t['age_days']:.0f}d ago, {t['source']}]")
print("\nMOST RELEVANT TOPICS FOR YOUR IDEA:")
for m in r["matches"]:
    print(f"  - {m['topic_text']:<45} score={m['score']:.2f} (sim={m['similarity']:.2f}, fresh={m['freshness']:.2f})")
print("\nCONTENT ANGLES:")
for i in r["ideas"]:
    print(f"  * {i['angle']}: {i['suggestion']}\n      evidence: {i['why']}")
