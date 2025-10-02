#!/usr/bin/env python3
# post_all.py

import os
import sys
import time
import shutil
import base64
import random
import pickle
import subprocess
import requests

# YouTube libs
import googleapiclient.discovery
import googleapiclient.http
from google.auth.transport.requests import Request

# ---------------- Configs ----------------
PENDING_DIR = "videos/pending"
POSTED_DIR = "videos/posted"
HTTP_SERVER_PORT = int(os.getenv("HTTP_SERVER_PORT", "8000"))
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")
NGROK_URL = os.getenv("NGROK_URL")  # Agora o URL público vem do GitHub Actions

CLIENT_SECRETS_FILE = "client_secret.json"
TOKEN_FILE = "token.pickle"

YT_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

CAPTIONS = [
    "🚀 Novo conteúdo no canal! Curtiu? Deixa um like e compartilha. #shorts #conteudo #aprenda",
    "🔥 Dica rápida pra você aplicar hoje — não esquece de salvar! #reels #aprendizado #viral",
    "🎯 Foco e consistência: pequenas ações, grandes resultados. #motivacao #shorts #trabalho"
]

def pick_caption():
    return random.choice(CAPTIONS)

def find_next_video():
    if not os.path.exists(PENDING_DIR):
        return None
    files = sorted([f for f in os.listdir(PENDING_DIR) if f.lower().endswith(('.mp4','.mov','.mkv','.avi'))])
    if not files:
        return None
    return os.path.join(PENDING_DIR, files[0])

# ---------------- YouTube ----------------
def setup_youtube_credentials_from_env():
    cs = os.getenv("YOUTUBE_CLIENT_SECRET_JSON")
    tok_b64 = os.getenv("YOUTUBE_TOKEN_PICKLE")
    if not cs:
        raise ValueError("YOUTUBE_CLIENT_SECRET_JSON não definido.")
    print("[INFO] Gravando client_secret.json...")
    with open(CLIENT_SECRETS_FILE, "w") as f:
        f.write(cs)
    if tok_b64:
        print("[INFO] Gravando token.pickle...")
        token_bytes = base64.b64decode(tok_b64.encode())
        with open(TOKEN_FILE, "wb") as f:
            f.write(token_bytes)

def get_authenticated_youtube():
    credentials = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            credentials = pickle.load(f)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            raise RuntimeError("Sem token válido do YouTube.")
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(credentials, f)
    return googleapiclient.discovery.build("youtube", "v3", credentials=credentials)

def upload_to_youtube(file_path, title, description, tags=None, category_id="22", privacy="public"):
    youtube = get_authenticated_youtube()
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
            "categoryId": category_id
        },
        "status": {"privacyStatus": privacy}
    }
    media = googleapiclient.http.MediaFileUpload(file_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while True:
        status, response = request.next_chunk()
        if status:
            print(f"[INFO] Upload YouTube: {int(status.progress() * 100)}%")
        if response:
            break
    print("[INFO] YouTube upload concluído ID:", response.get("id"))
    return response

# ---------------- Instagram ----------------
def upload_instagram_reel(video_public_url, caption):
    print(f"[INFO] Criando reel no Instagram com URL: {video_public_url}")
    url = f"https://graph.facebook.com/v20.0/{IG_USER_ID}/media"
    data = {
        "caption": caption,
        "media_type": "REELS",
        "video_url": video_public_url,
        "access_token": IG_ACCESS_TOKEN
    }
    resp = requests.post(url, data=data).json()
    print("[INFO] Resposta upload IG:", resp)
    return resp

def publish_instagram(container_id):
    print(f"[INFO] Publicando reel IG com ID: {container_id}")
    url = f"https://graph.facebook.com/v20.0/{IG_USER_ID}/media_publish"
    data = {"creation_id": container_id, "access_token": IG_ACCESS_TOKEN}
    resp = requests.post(url, data=data).json()
    print("[INFO] Resposta publish IG:", resp)
    return resp

# ---------------- Runner ----------------
def main():
    os.makedirs(PENDING_DIR, exist_ok=True)
    video_path = find_next_video()
    if not video_path:
        print("[INFO] Nenhum vídeo em pending.")
        return

    print(f"[INFO] Próximo vídeo a postar: {os.path.basename(video_path)}")
    caption = pick_caption()
    print(f"[INFO] Legenda escolhida: {caption}")

    print("[INFO] Iniciando servidor HTTP local...")
    http_proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(HTTP_SERVER_PORT), "--directory", PENDING_DIR],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2)

    ig_success = yt_success = False
    try:
        if not NGROK_URL:
            raise RuntimeError("NGROK_URL não definido!")

        video_file = os.path.basename(video_path)
        video_public_url = f"{NGROK_URL}/{video_file}"

        # Instagram
        if IG_ACCESS_TOKEN and IG_USER_ID:
            up_resp = upload_instagram_reel(video_public_url, caption)
            if "id" in up_resp:
                print("[INFO] Reel criado com sucesso no IG, aguardando 30s antes de publicar...")
                time.sleep(30)
                pub_resp = publish_instagram(up_resp["id"])
                if "id" in pub_resp:
                    ig_success = True

        # YouTube
        if os.getenv("YOUTUBE_CLIENT_SECRET_JSON"):
            try:
                setup_youtube_credentials_from_env()
                title = os.path.splitext(os.path.basename(video_path))[0][:100]
                desc = caption + "\n\nPublicado automaticamente."
                upload_resp = upload_to_youtube(video_path, title, desc, tags=["shorts","automacao"])
                if "id" in upload_resp:
                    yt_success = True
            except Exception as e:
                print("[ERROR] Erro YouTube:", e)

    finally:
        if http_proc: 
            http_proc.kill()
            print("[INFO] Servidor HTTP finalizado.")

    if ig_success or yt_success:
        os.makedirs(POSTED_DIR, exist_ok=True)
        shutil.move(video_path, os.path.join(POSTED_DIR, os.path.basename(video_path)))
        print("[INFO] Vídeo movido para posted.")
    else:
        print("[WARN] Falha em ambos — vídeo mantido em pending.")

if __name__ == "__main__":
    main()
