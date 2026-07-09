import pandas as pd

stories = pd.read_csv("data/stories_metadata.csv")

print(stories.head())
print()

print(f"Loaded {len(stories)} stories.")