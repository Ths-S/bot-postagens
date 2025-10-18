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
IG_USER_ID = os.getenv("z")

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

        res = youtube.videos().list(part="statistics", id=video_id).execute()
        if "items" not in res or len(res["items"]) == 0:
            continue

        stats = res["items"][0]["statistics"]
        video_metrics.append({
            "gancho": gancho_nome,
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
    print("📸 Coletando métricas do Instagram...")

    base_url = "https://graph.facebook.com/v20.0"
    token = GRAPH_API_TOKEN
    user_id = IG_USER_ID

    # 1️⃣ Coleta todos os IDs das postagens (com paginação)
    post_ids = []
    url = f"{base_url}/{user_id}/media?access_token={token}"

    try:
        while url:
            r = requests.get(url)
            data = r.json()

            if "error" in data:
                print("❌ Erro retornado pela API:", data["error"])
                return {"summary": {}, "posts": []}

            batch = data.get("data", [])
            post_ids.extend([p["id"] for p in batch if "id" in p])

            url = data.get("paging", {}).get("next")  # próxima página

        if not post_ids:
            print("⚠️ Nenhum ID de post encontrado. Verifique GRAPH_API_TOKEN e IG_USER_ID.")
            return {"summary": {}, "posts": []}

        print(f"📄 {len(post_ids)} IDs de posts coletados.")
    except Exception as e:
        print("❌ Erro ao coletar IDs de posts:", e)
        return {"summary": {}, "posts": []}

    # 2️⃣ Coleta dados de cada post individualmente
    insta_metrics = []
    total_likes = total_comments = 0

    fields = (
        "id,caption,media_type,media_url,thumbnail_url,timestamp,"
        "permalink,like_count,comments_count,children{media_url,media_type}"
    )

    for post_id in post_ids:
        try:
            res = requests.get(f"{base_url}/{post_id}?fields={fields}&access_token={token}")
            post = res.json()

            if "error" in post:
                print(f"⚠️ Erro ao buscar dados do post {post_id}: {post['error']}")
                continue

            caption = post.get("caption", "")
            like_count = int(post.get("like_count", 0))
            comments_count = int(post.get("comments_count", 0))
            total_likes += like_count
            total_comments += comments_count

            # Tenta associar com metadados locais
            match = next(
                (v for k, v in metadata.items() if caption and caption.strip() in v.get("description", "")),
                None
            )

            insta_metrics.append({
                "id": post_id,
                "caption": caption,
                "media_type": post.get("media_type"),
                "media_url": post.get("media_url"),
                "thumbnail_url": post.get("thumbnail_url"),
                "permalink": post.get("permalink"),
                "timestamp": post.get("timestamp"),
                "likes": like_count,
                "comments": comments_count,
                "children": post.get("children", {}).get("data", []),
                "matched_metadata": match
            })

        except Exception as e:
            print(f"⚠️ Falha ao coletar post {post_id}: {e}")
            continue

    # 3️⃣ Resumo geral
    summary = {
        "totalPosts": len(insta_metrics),
        "totalLikes": total_likes,
        "totalComments": total_comments,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }

    print(f"✅ Coletados {len(insta_metrics)} posts do Instagram com sucesso.")
    return {"summary": summary, "posts": insta_metrics}


# =======================
# 🔹 AUTENTICAÇÃO YOUTUBE
# =======================
def get_youtube_service():
    token_pickle_data = os.getenv("TOKEN_PICKLE_COMPLETE")
    if not token_pickle_data:
        raise Exception("TOKEN_PICKLE_COMPLETE não encontrado!")

    token_pickle_bytes = pickle.loads(base64.b64decode(token_pickle_data))
    return build("youtube", "v3", credentials=token_pickle_bytes)

# =======================
# 🔹 EXECUÇÃO PRINCIPAL
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

# =======================
# 🔹 COMMIT AUTOMÁTICO
# =======================
def git_commit_metrics():
    subprocess.run(["git", "config", "--global", "user.name", "github-actions"], check=True)
    subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], check=True)
    subprocess.run(["git", "add", "data/metrics.json"], check=True)
    subprocess.run(["git", "commit", "-m", "Atualiza métricas do YouTube e Instagram"], check=False)
    subprocess.run(["git", "push"], check=False)

git_commit_metrics()
