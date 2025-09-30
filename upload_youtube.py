import os
import pickle
import base64
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

VIDEO_FILE = "videos/video.mp4"  # caminho do vídeo
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_credentials():
    client_secret_json = os.environ.get("YOUTUBE_CLIENT_SECRET_JSON")
    token_pickle_b64 = os.environ.get("YOUTUBE_TOKEN_PICKLE")

    if not client_secret_json:
        raise ValueError("Variável YOUTUBE_CLIENT_SECRET_JSON não definida.")
    
    client_config = json.loads(client_secret_json)

    credentials = None
    if token_pickle_b64:
        token_bytes = base64.b64decode(token_pickle_b64)
        credentials = pickle.loads(token_bytes)
    
    # Se não houver token válido, faz o fluxo de OAuth
    if not credentials or not credentials.valid:
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        credentials = flow.run_console()
        print("Novo token gerado. Você pode atualizar a variável YOUTUBE_TOKEN_PICKLE no GitHub Actions.")

    return credentials

def upload_video(file_path):
    credentials = get_credentials()
    youtube = build("youtube", "v3", credentials=credentials)

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": "Título do Vídeo",
                "description": "Descrição do vídeo",
                "tags": ["teste", "upload", "api"],
                "categoryId": "22"  # Categoria: People & Blogs
            },
            "status": {
                "privacyStatus": "private"
            }
        },
        media_body=MediaFileUpload(file_path)
    )

    response = request.execute()
    print("Upload concluído. Video ID:", response.get("id"))

if __name__ == "__main__":
    if not os.path.exists(VIDEO_FILE):
        raise FileNotFoundError(f"Arquivo {VIDEO_FILE} não encontrado.")
    upload_video(VIDEO_FILE)
