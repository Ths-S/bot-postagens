import os
import json
import datetime
import requests
from googleapiclient.discovery import build
import pickle
import base64
import subprocess

# Caminhos
os.makedirs("data", exist_ok=True)
metrics_path = "data/metrics.json"
metadata_path = "metadata.json"

# Variáveis de ambiente (GitHub Secrets)
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
GRAPH_API_TOKEN = os.getenv("GRAPH_API_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")

# =======================
# 🔹 FUNÇÕES DO YOUTUBE
# =======================
def get_youtube_metrics(youtube, metadata):
    channel_stats = youtube.channels().list(part="statistics", mine=True).execute()
    channel_data = channel_stats["items"][0]["statistics"]

    video_metrics = []
    for gancho_nome, info in metadata.items():
        title = info.get("title", "")
        video_id = info.get("youtube_id")

        if not video_id:
            continue

        res = youtube.videos().list(part="snippet,statistics", id=video_id).execute()
        if not res.get("items"):
            continue

        snippet = res["items"][0]["snippet"]
        stats = res["items"][0]["statistics"]

        video_metrics.append({
            "gancho": gancho_nome,
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
            "publishedAt": snippet.get("publishedAt", ""),
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
    base_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}"
    fields = (
        "username,followers_count,follows_count,media_count,"
        "media{id,caption,media_type,permalink,like_count,comments_count,timestamp,"
        "insights.metric(impressions,reach,engagement)}"
    )
    url = f"{base_url}?fields={fields}&access_token={GRAPH_API_TOKEN}"

    r = requests.get(url)
    data = r.json()

    if "error" in data:
        print("⚠️ Erro na Graph API:", data["error"])
        return []

    insta_metrics = {
        "summary": {
            "username": data.get("username", ""),
            "followers": data.get("followers_count", 0),
            "following": data.get("follows_count", 0),
            "media_count": data.get("media_count", 0),
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        },
        "posts": []
    }

    media_items = data.get("media", {}).get("data", [])
    for post in media_items:
        insights = {}
        if "insights" in post and "data" in post["insights"]:
            for metric in post["insights"]["data"]:
                insights[metric["name"]] = metric["values"][0]["value"]

        insta_metrics["posts"].append({
            "id": post["id"],
            "caption": post.get("caption", ""),
            "media_type": post.get("media_type", ""),
            "permalink": post.get("permalink", ""),
            "timestamp": post.get("timestamp", ""),
            "likes": post.get("like_count", 0),
            "comments": post.get("comments_count", 0),
            "reach": insights.get("reach", 0),
            "impressions": insights.get("impressions", 0),
            "engagement": insights.get("engagement", 0),
        })

    return insta_metrics

# =======================
# 🔹 YOUTUBE SERVICE
# =======================
def get_youtube_service():
    token_pickle_data = os.getenv("TOKEN_PICKLE_COMPLETE")
    if not token_pickle_data:
        raise Exception("TOKEN_PICKLE_COMPLETE não encontrado!")

    token_pickle_bytes = pickle.loads(base64.b64decode(token_pickle_data))
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

# =======================
# 🔹 COMMIT AUTOMÁTICO
# =======================
def git_commit_metrics():
    subprocess.run(["git", "config", "--global", "user.name", "github-actions"], check=True)
    subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], check=True)
    subprocess.run(["git", "add", "data/metrics.json"], check=True)
    subprocess.run(["git", "commit", "-m", "Atualiza métricas YouTube e Instagram"], check=False)
    subprocess.run(["git", "push"], check=False)

if __name__ == "__main__":
    main()
    git_commit_metrics()
