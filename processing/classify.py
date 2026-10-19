"""Rule-based domain tagging (Gaming / Education / Cooking / Other).
Starter keyword lists -- extend with the team's own Sri Lankan vocabulary.
TODO: add Sinhala-script + Romanised-Sinhala terms (teammate's localisation work), and later an
embedding-prototype classifier for topics the keywords miss."""
import re

KEYWORDS = {
    "Gaming": ["minecraft", "roblox", "free fire", "pubg", "bgmi", "gta", "fortnite", "valorant", "call of duty",
               "cod mobile", "mobile legends", "fifa", "ea fc", "ps5", "xbox", "steam", "esports", "gameplay",
               "walkthrough", "speedrun", "survival", "hardcore", "game", "gaming", "gamer", "twitch", "pokemon",
               "elden ring", "among us", "clash of clans", "league of legends", "dota"],
    "Education": ["o/l", "a/l", "al exam", "past paper", "scholarship", "grade 5", "grade 11", "exam",
                  "syllabus", "tutorial", "lesson", "learn", "course", "university", "sliit", "ict", "maths",
                  "science", "english", "study", "tuition", "ielts", "python", "coding", "programming",
                  "ai tools", "chatgpt", "results", "z-score", "z score", "degree", "free certificate"],
    "Cooking": ["recipe", "cooking", "cook", "kottu", "hoppers", "string hoppers", "pol sambol", "lamprais", "curry",
                "rice", "watalappan", "kiribath", "biryani", "cake", "baking", "street food", "dessert",
                "sambol", "dhal", "parippu", "fish curry", "ambul thiyal", "kokis", "pasta", "chicken", "food",
                "kitchen", "airfryer", "air fryer", "vegan", "breakfast", "dinner"],
}


def classify(text: str) -> str:
    t = " " + re.sub(r"\s+", " ", text.lower()) + " "
    scores = {d: sum(1 for k in kws if k in t) for d, kws in KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "Other"
