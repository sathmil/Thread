"""Generates a clearly-synthetic, templated story set for load-testing the
upload/index pipeline at a scale (~50-200 stories) the original 10-story
WHO WE ARE dataset can't exercise. Not real submissions — do not present
this as authentic personal narrative data.
"""
import csv
import random
import sys
from pathlib import Path

THEMES = [
    ("school", "the hallway lights flickered every morning before first period"),
    ("family", "my grandmother kept a jar of buttons on the windowsill"),
    ("moving", "we packed the same six boxes every autumn"),
    ("language", "I translate for my parents at the pharmacy every month"),
    ("music", "the choir room smelled like rosin and old carpet"),
    ("sports", "practice started before the sun came up"),
    ("food", "Sunday dinner took four hours and nobody minded"),
    ("silence", "some questions in our house were never asked out loud"),
    ("mentorship", "she waited by the gate until I figured it out myself"),
    ("distance", "the bus ride home was forty minutes of staring out the window"),
]


def generate_synthetic_stories(n: int, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    stories = []
    for i in range(n):
        theme, opener = THEMES[i % len(THEMES)]
        sentences = [
            f"{opener[0].upper()}{opener[1:]}.",
            f"I thought about {theme} more than I let on.",
            "Some days it felt ordinary. Other days it felt like the whole story.",
            f"By the time I understood what {theme} meant to me, things had already changed.",
            "I did not have the words for it then, but I do now.",
        ]
        rng.shuffle(sentences)
        stories.append({"id": f"synthetic-{i + 1:04d}", "story_text": " ".join(sentences)})
    return stories


def write_csv(path: Path, n: int) -> None:
    stories = generate_synthetic_stories(n)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["id", "story_text"])
        writer.writeheader()
        writer.writerows(stories)


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("synthetic_stories.csv")
    write_csv(out_path, count)
    print(f"Wrote {count} synthetic stories to {out_path}")
