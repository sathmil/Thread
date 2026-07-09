import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import DATA_PATH, EMBEDDINGS_PATH

# 1. Load your stories
df = pd.read_csv(DATA_PATH)

# 2. Get the text column
stories = df["story_text"].fillna("").tolist()

print(f"Loaded {len(stories)} stories.")

# 3. Load a pretrained embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# 4. Generate embeddings
embeddings = model.encode(stories, show_progress_bar=True)

print("Embeddings shape:", embeddings.shape)

# 5. Save embeddings
np.save(EMBEDDINGS_PATH, embeddings)

print(f"Saved embeddings to {EMBEDDINGS_PATH}")