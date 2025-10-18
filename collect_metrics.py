import os
import json
import datetime
import requests
from googleapiclient.discovery import build
import pickle
import base64


# Caminhos
os.makedirs("data", exist_ok=True)
metrics_path = "data/metrics.json"
metadata_path = "metadata.json"

# Variáveis de ambiente (GitHub Secrets)
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")

# =======================
# 🔹 FUNÇÕES DO YOUTUBE
# =======================
def get_youtube_metrics(youtube, metadata):
    channel_stats = youtube.channels().list(part="statistics", mine=True).execute()
    channel_data = channel_stats["items"][0]["statistics"]

    # Dados de vídeos individuais por gancho
    video_metrics = []
    for gancho_nome, info in metadata.items():
        title = info.get("title", "")
        video_id = info.get("youtube_id")  # precisa existir no metadata.json

        if not video_id:
            continue  # ignora ganchos sem vídeo associado

        res = youtube.videos().list(part="statistics", id=video_id).execute()
        if "items" not in res or len(res["items"]) == 0:
            continue

        stats = res["items"][0]["statistics"]
        video_metrics.append({
            "gancho": gancho_nome,  # nome do gancho (gancho1, gancho2, etc.)
            "title": title,
            "video_id": video_id,
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0))
        })

    return {
        "summary": {
            "viewCount": int(channel_data["viewCount"]),
            "subscriberCount": int(channel_data["subscriberCount"]),
            "videoCount": int(channel_data["videoCount"]),
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        },
        "videos": video_metrics
    }

# =======================
# 🔹 FUNÇÕES DO INSTAGRAM
# =======================
def get_instagram_metrics(metadata):
    url = f"https://graph.instagram.com/{IG_USER_ID}/media?fields=id,caption,media_type,permalink,like_count,comments_count&access_token={IG_ACCESS_TOKEN}"
    r = requests.get(url)
    data = r.json()

    insta_metrics = []
    if "data" in data:
        for post in data["data"]:
            caption = post.get("caption", "")
            like_count = post.get("like_count", 0)
            comments_count = post.get("comments_count", 0)
            match = next((v for k, v in metadata.items() if caption.strip() in v.get("description", "")), None)
            insta_metrics.append({
                "id": post["id"],
                "caption": caption,
                "likes": like_count,
                "comments": comments_count,
                "matched_metadata": match
            })

    return insta_metrics

def get_youtube_service():
    token_pickle_data = os.getenv("TOKEN_PICKLE_COMPLETE")
    if not token_pickle_data:
        raise Exception("TOKEN_PICKLE_COMPLETE não encontrado!")

    import pickle, base64
    token_pickle_bytes = pickle.loads(base64.b64decode(token_pickle_data))
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=token_pickle_bytes)


# =======================
# 🔹 FUNÇÃO PRINCIPAL
# =======================
def main():
    print("📊 Coletando métricas...")

    if not os.path.exists(metadata_path):
        raise FileNotFoundError("metadata.json não encontrado!")

    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    youtube = get_youtube_service()
    youtube_data = get_youtube_metrics(youtube, metadata)
    instagram_data = get_instagram_metrics(metadata)

    final_data = {
        "youtube": youtube_data,
        "instagram": instagram_data
    }

    with open(metrics_path, "w") as f:
        json.dump(final_data, f, indent=4)

    print("✅ Métricas salvas em", metrics_path)

if __name__ == "__main__":
    main()


import subprocess

def git_commit_metrics():
    subprocess.run(["git", "config", "--global", "user.name", "github-actions"], check=True)
    subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], check=True)
    subprocess.run(["git", "add", "data/metrics.json"], check=True)
    subprocess.run(["git", "commit", "-m", "Atualiza métricas do YouTube"], check=False)
    subprocess.run(["git", "push"], check=False)

git_commit_metrics()
