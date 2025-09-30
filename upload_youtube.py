import os
import pickle
import json
import base64
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.http
from google.auth.transport.requests import Request

VIDEO_FOLDER = "videos/pending"
CLIENT_SECRETS_FILE = "client_secret.json"
TOKEN_FILE = "token.pickle"

def setup_credentials_files():
    """Cria os arquivos de credenciais a partir das variáveis de ambiente."""
    client_secret_json = os.getenv("YOUTUBE_CLIENT_SECRET_JSON")
    token_pickle_b64 = os.getenv("YOUTUBE_TOKEN_PICKLE")

    if not client_secret_json:
        raise Exception("YOUTUBE_CLIENT_SECRET_JSON não encontrado nos secrets.")

    # Salva client_secret.json
    with open(CLIENT_SECRETS_FILE, "w") as f:
        f.write(client_secret_json)

    # Se existir token salvo em base64, cria o token.pickle
    if token_pickle_b64:
        token_bytes = base64.b64decode(token_pickle_b64.encode())
        with open(TOKEN_FILE, "wb") as f:
            f.write(token_bytes)

def get_authenticated_service():
    scopes = ["https://www.googleapis.com/auth/youtube.upload"]
    credentials = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            credentials = pickle.load(f)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, scopes
            )
            credentials = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(credentials, f)

    return googleapiclient.discovery.build("youtube", "v3", credentials=credentials)

def upload_video(file_path, title, description, tags=None, category_id="22", privacy="public"):
    youtube = get_authenticated_service()

    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags if tags else [],
            "categoryId": category_id
        },
        "status": {
            "privacyStatus": privacy
        }
    }

    media = googleapiclient.http.MediaFileUpload(file_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media
    )
    response = request.execute()
    print("✅ Upload concluído! ID do vídeo:", response["id"])

if __name__ == "__main__":
    setup_credentials_files()

    for file in os.listdir(VIDEO_FOLDER):
        if file.lower().endswith((".mp4", ".mov", ".avi", ".mkv")):
            video_path = os.path.join(VIDEO_FOLDER, file)
            upload_video(
                file_path=video_path,
                title="Meu Short automático",
                description="Publicado automaticamente via API",
                tags=["shorts", "python", "automação"]
            )
            break
