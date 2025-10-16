# collect_metrics.py
import os
import json
import time
import requests
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

YOUTUBE_OAUTH_JSON = os.getenv("YOUTUBE_OAUTH_JSON")  # <-- GitHub Secret (conteúdo JSON)
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")

os.makedirs("data", exist_ok=True)
metrics_path = "data/metrics.json"

SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

def load_credentials_from_env():
    """
    Espera um JSON com: token, refresh_token, token_uri, client_id, client_secret, scopes
    (o mesmo que o script generate_youtube_oauth_json imprime).
    """
    if not YOUTUBE_OAUTH_JSON:
        return None
    try:
        info = json.loads(YOUTUBE_OAUTH_JSON)
    except Exception as e:
        print("Erro ao parsear YOUTUBE_OAUTH_JSON:", e)
        return None

    creds = Credentials(
        token=info.get("token"),
        refresh_token=info.get("refresh_token"),
        token_uri=info.get("token_uri"),
        client_id=info.get("client_id"),
        client_secret=info.get("client_secret"),
        scopes=info.get("scopes", SCOPES),
    )

    # Se token expirado, tenta refresh automaticamente
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # opcional: você pode exportar o novo token atualizado para logs (cuidado com segredos)
        except Exception as e:
            print("Falha ao atualizar token:", e)
    return creds

def get_youtube_service():
    creds = load_credentials_from_env()
    if not creds:
        raise RuntimeError("Nenhuma credencial do YouTube encontrada. Configure YOUTUBE_OAUTH_JSON no GitHub Secrets.")
    service = build("youtube", "v3", credentials=creds)
    return service

def get_youtube_metrics():
    youtube = get_youtube_service()

    # Exemplo: pegar vídeos curtidos (myRating requires OAuth) - isto retorna uma lista de vídeos "like"
    request = youtube.videos().list(part="snippet,statistics", myRating="like", maxResults=50)
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
            "videoId": item.get("id"),
        })
    return metrics

def get_instagram_metrics():
    if not IG_ACCESS_TOKEN or not IG_USER_ID:
        print("IG_ACCESS_TOKEN ou IG_USER_ID não configurados. Pulando Instagram.")
        return []
    url = f"https://graph.facebook.com/v20.0/{IG_USER_ID}/media?fields=id,caption,like_count,comments_count,media_type,media_url,permalink,timestamp&access_token={IG_ACCESS_TOKEN}"
    resp = requests.get(url)
    try:
        data = resp.json()
    except Exception:
        print("Resposta inválida do Instagram:", resp.text)
        return []

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
    try:
        youtube_data = get_youtube_metrics()
    except Exception as e:
        print("Erro ao coletar métricas do YouTube:", e)
        youtube_data = []

    insta_data = get_instagram_metrics()

    all_data = {"youtube": youtube_data, "instagram": insta_data, "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    print("✅ Métricas salvas em data/metrics.json")

if __name__ == "__main__":
    main()
