import os
import json
import pickle
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# Pasta e arquivos
os.makedirs("data", exist_ok=True)
METRICS_PATH = "data/metrics.json"
TOKEN_FILE = "token.pickle"

# Salva token do GitHub Secret em token.pickle
if not os.path.exists(TOKEN_FILE):
    token_base64 = os.getenv("TOKEN_PICKLE_COMPLETE")
    if not token_base64:
        raise Exception("TOKEN_PICKLE_COMPLETE não encontrado nos Secrets do GitHub!")
    import base64
    with open(TOKEN_FILE, "wb") as f:
        f.write(base64.b64decode(token_base64))

def get_youtube_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise Exception("Token inválido ou expirado e não é possível atualizar automaticamente no Actions.")

    return build("youtube", "v3", credentials=creds)

def get_youtube_metrics():
    try:
        service = get_youtube_service()
        request = service.channels().list(part="statistics", mine=True)
        response = request.execute()
        return response
    except Exception as e:
        print(f"Erro ao coletar métricas do YouTube: {e}")
        return {}

def save_metrics(metrics):
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"✅ Métricas salvas em {METRICS_PATH}")

def main():
    print("📊 Coletando métricas...")
    youtube_data = get_youtube_metrics()
    save_metrics({"youtube": youtube_data})

if __name__ == "__main__":
    main()
