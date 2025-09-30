import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import googleapiclient.discovery
import googleapiclient.http

VIDEO_FOLDER = "videos"
CLIENT_SECRETS_FILE = "client_secret.json"
TOKEN_FILE = "token.pickle"

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_authenticated_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    # Se token expirou, atualiza automaticamente usando refresh token
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise Exception("Token inválido ou ausente. Gere um refresh token e salve no GitHub Secrets.")

        # Salva novamente para próximos usos
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)

    return googleapiclient.discovery.build("youtube", "v3", credentials=creds)

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
    print("Upload concluído! ID do vídeo:", response["id"])

if __name__ == "__main__":
    for file in os.listdir(VIDEO_FOLDER):
        if file.lower().endswith((".mp4", ".mov", ".avi", ".mkv")):
            upload_video(
                file_path=os.path.join(VIDEO_FOLDER, file),
                title="Meu Short Automático",
                description="Publicado automaticamente via API",
                tags=["shorts", "python", "automação"]
            )
            break
