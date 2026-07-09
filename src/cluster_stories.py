import pandas as pd
import numpy as np
from sklearn.cluster import KMeans

# 1. Load stories and embeddings
df = pd.read_csv("data/stories_metadata.csv")
embeddings = np.load("data/story_embeddings.npy")

print(f"Loaded {len(df)} stories.")
print("Embeddings shape:", embeddings.shape)

# 2. Choose number of clusters
# Since you only have 10 stories, start with 3 clusters.
num_clusters = 3

# 3. Run KMeans clustering
kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10)
cluster_labels = kmeans.fit_predict(embeddings)

# 4. Add cluster labels to dataframe
df["cluster"] = cluster_labels

# 5. Save results
df.to_csv("data/clustered_stories.csv", index=False)

print("Saved clustered stories to data/clustered_stories.csv")
print()

# 6. Print stories grouped by cluster
for cluster_id in sorted(df["cluster"].unique()):
    print("=" * 50)
    print(f"CLUSTER {cluster_id}")
    print("=" * 50)

    cluster_stories = df[df["cluster"] == cluster_id]

    for _, row in cluster_stories.iterrows():
        preview = row["story_text"][:200].replace("\n", " ")
        print(f"Story {row['id']}: {preview}...")
        print()