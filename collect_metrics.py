import os
import json
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

# Pasta e arquivos
os.makedirs("data", exist_ok=True)
METRICS_PATH = "data/metrics.json"
CLIENT_SECRETS_FILE = "client_secret.json"
TOKEN_FILE = "token.pickle"

# Escopos do YouTube
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

# Salva o secret do GitHub em client_secret.json se não existir
if not os.path.exists(CLIENT_SECRETS_FILE):
    oauth_json = os.getenv("YOUTUBE_OAUTH_JSON")
    if not oauth_json:
        raise Exception("YOUTUBE_OAUTH_JSON não encontrado nos Secrets do GitHub!")
    with open(CLIENT_SECRETS_FILE, "w") as f:
        f.write(oauth_json)

def get_youtube_service():
    creds = None
    # Verifica se já existe token
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    # Se não tiver credenciais válidas, faz login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Salva o token para a próxima vez
        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)

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
