import pandas as pd

from app.config import DATA_PATH

stories = pd.read_csv(DATA_PATH)

print(stories.head())
print()

print(f"Loaded {len(stories)} stories.")