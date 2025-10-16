import os
import json
import base64
import pickle
from datetime import datetime
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# === Caminho do arquivo de saída ===
os.makedirs("data", exist_ok=True)
metrics_path = "data/metrics.json"


def log(msg):
    print(f"📊 {msg}")


def get_youtube_service():
    """Lê o token do GitHub Secrets e inicializa o serviço da API YouTube"""
    token_b64 = os.getenv("TOKEN_PICKLE_COMPLETE")

    if not token_b64:
        raise Exception("❌ TOKEN_PICKLE_COMPLETE não encontrado nos Secrets do GitHub!")

    # Decodifica o token para arquivo temporário
    token_bytes = base64.b64decode(token_b64)
    with open("token_temp.pickle", "wb") as f:
        f.write(token_bytes)

    with open("token_temp.pickle", "rb") as token_file:
        creds = pickle.load(token_file)

    # Renova o token se necessário
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return build("youtube", "v3", credentials=creds)


def get_youtube_metrics():
    """Obtém estatísticas do canal YouTube"""
    youtube = get_youtube_service()
    request = youtube.channels().list(part="statistics", mine=True)
    response = request.execute()

    stats = response["items"][0]["statistics"]
    return {
        "viewCount": int(stats.get("viewCount", 0)),
        "subscriberCount": int(stats.get("subscriberCount", 0)),
        "videoCount": int(stats.get("videoCount", 0)),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def main():
    log("Coletando métricas...")

    try:
        youtube_data = get_youtube_metrics()
    except Exception as e:
        log(f"Erro ao coletar métricas do YouTube: {e}")
        youtube_data = {}

    # Junta tudo num dicionário
    metrics = {"youtube": youtube_data}

    # Salva no arquivo JSON
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=4)

    log("✅ Métricas salvas com sucesso!")
    print(f"📁 Caminho completo: {os.path.abspath(metrics_path)}")


if __name__ == "__main__":
    main()
