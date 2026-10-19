"""Run all collectors once (this is what GitHub Actions calls).
   python collect.py            -> Google Trends + YouTube + manual CSV
   python collect.py --seed     -> also load the SAMPLE demo topics (clearly labelled sample_seed)"""
import sys

from collectors import google_trends, manual_import, youtube

if __name__ == "__main__":
    print(google_trends.run())
    print(youtube.run())
    manual_import.run_manual()
    if "--seed" in sys.argv:
        manual_import.run_seed()
