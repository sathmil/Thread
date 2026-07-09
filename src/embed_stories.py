import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer

# 1. Load your stories
df = pd.read_csv("data/stories_metadata.csv")

# 2. Get the text column
stories = df["story_text"].fillna("").tolist()

print(f"Loaded {len(stories)} stories.")

# 3. Load a pretrained embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# 4. Generate embeddings
embeddings = model.encode(stories, show_progress_bar=True)

print("Embeddings shape:", embeddings.shape)

# 5. Save embeddings
np.save("data/story_embeddings.npy", embeddings)

print("Saved embeddings to data/story_embeddings.npy")