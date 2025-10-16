import os
import json
import requests
from googleapiclient.discovery import build

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")

os.makedirs("data", exist_ok=True)
metrics_path = "data/metrics.json"

def get_youtube_metrics():
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    request = youtube.videos().list(
        part="snippet,statistics",
        myRating="like"  # apenas vídeos do canal autenticado
    )
    response = request.execute()

    metrics = []
    for item in response.get("items", []):
        stats = item.get("statistics", {})
        snippet = item.get("snippet", {})
        metrics.append({
            "title": snippet.get("title"),
            "publishedAt": snippet.get("publishedAt"),
            "views": int(stats.get("viewCount", 0)),
            "likes": int(stats.get("likeCount", 0)),
            "comments": int(stats.get("commentCount", 0)),
        })
    return metrics

def get_instagram_metrics():
    url = f"https://graph.facebook.com/v20.0/{IG_USER_ID}/media?fields=id,caption,like_count,comments_count,media_type,media_url,permalink,timestamp&access_token={IG_ACCESS_TOKEN}"
    resp = requests.get(url)
    data = resp.json()

    metrics = []
    for item in data.get("data", []):
        metrics.append({
            "caption": item.get("caption"),
            "likes": item.get("like_count"),
            "comments": item.get("comments_count"),
            "timestamp": item.get("timestamp"),
            "permalink": item.get("permalink"),
        })
    return metrics

def main():
    print("📊 Coletando métricas...")
    youtube_data = get_youtube_metrics()
    insta_data = get_instagram_metrics()

    all_data = {"youtube": youtube_data, "instagram": insta_data}
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    print("✅ Métricas salvas em data/metrics.json")

if __name__ == "__main__":
    main()
