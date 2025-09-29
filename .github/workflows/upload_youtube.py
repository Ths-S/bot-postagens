import os
import pickle
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.http

VIDEO_FOLDER = "videos"
CLIENT_SECRETS_FILE = "client_secret.json"
TOKEN_FILE = "token.pickle"  # arquivo para salvar credenciais

def get_authenticated_service():
    scopes = ["https://www.googleapis.com/auth/youtube.upload"]
    credentials = None

    # Tenta carregar token salvo
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            credentials = pickle.load(f)

    # Se não existir ou estiver expirado, faz login
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, scopes)
            credentials = flow.run_local_server(port=0)
        # Salva o token para próximos usos
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
    print("Upload concluído! ID do vídeo:", response["id"])

if __name__ == "__main__":
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
