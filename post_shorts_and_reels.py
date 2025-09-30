#!/usr/bin/env python3
"""
post_shorts_and_reels.py
- Pega o primeiro vídeo em videos/pending
- Gera 1 das 3 legendas (aleatórias)
- Faz upload para YouTube (Shorts) e Instagram Reels
- Move o arquivo para videos/posted se ambos os uploads retornarem sucesso
- Não re-encoda o vídeo (usa o arquivo original)
- Usa variáveis de ambiente para credenciais (apropriado para GitHub Actions)
"""

import os
import sys
import time
import random
import shutil
import base64
import pickle
import subprocess
from pathlib import Path

import requests

# libs para youtube
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.http
from google.auth.transport.requests import Request

# ---- Config ----
PENDING_DIR = Path("videos/pending")
POSTED_DIR = Path("videos/posted")

# YouTube
CLIENT_SECRETS_FILE = "client_secret.json"
TOKEN_FILE = "token.pickle"
YOUTUBE_CATEGORY = "22"  # "People & Blogs" — ajuste se quiser
YOUTUBE_PRIVACY = "public"

# Instagram (Graph API)
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")

# Optional NGROK token (se quiser usar ngrok para expor local http server)
NGROK_AUTH_TOKEN = os.getenv("NGROK_AUTH_TOKEN")

# Optional base caption prefix
CAPTION_PREFIX = os.getenv("CAPTION_PREFIX", "")

# ---- Helpers ----
def setup_youtube_credentials_from_env():
    """
    Cria client_secret.json e token.pickle a partir das variáveis de ambiente:
    - YOUTUBE_CLIENT_SECRET_JSON : conteudo JSON do client_secret (string)
    - YOUTUBE_TOKEN_PICKLE : token.pickle em base64 (opcional — preferível)
    """
    client_secret_json = os.getenv("YOUTUBE_CLIENT_SECRET_JSON")
    token_pickle_b64 = os.getenv("YOUTUBE_TOKEN_PICKLE")

    if not client_secret_json:
        print("⚠️ YOUTUBE_CLIENT_SECRET_JSON não encontrado nas envs. O upload do YouTube falhará sem credenciais.")
        return False

    with open(CLIENT_SECRETS_FILE, "w", encoding="utf-8") as f:
        f.write(client_secret_json)
    print("✅ client_secret.json salvo.")

    if token_pickle_b64:
        try:
            token_bytes = base64.b64decode(token_pickle_b64.encode())
            with open(TOKEN_FILE, "wb") as f:
                f.write(token_bytes)
            print("✅ token.pickle salvo a partir da variável de ambiente.")
        except Exception as e:
            print("❌ Erro ao criar token.pickle:", e)
            return False

    return True

def get_youtube_service():
    scopes = ["https://www.googleapis.com/auth/youtube.upload"]
    credentials = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            credentials = pickle.load(f)
        print("✅ Token carregado de token.pickle")

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            print("🔄 Atualizando token expirado...")
            credentials.refresh(Request())
        else:
            # No GitHub Actions você deve fornecer token.pickle via secret (base64) — sem interação.
            raise RuntimeError("Nenhum token válido disponível para YouTube. Providencie YOUTUBE_TOKEN_PICKLE nas Secrets.")
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(credentials, f)

    return googleapiclient.discovery.build("youtube", "v3", credentials=credentials)

def upload_to_youtube(file_path: Path, title: str, description: str, tags=None, dry_run=False):
    print(f"📤 YouTube upload: {file_path}")
    if dry_run:
        print("🧪 Dry run do YouTube (simulação).")
        return {"id": "SIMULATED_YT_ID"}

    youtube = get_youtube_service()
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
            "categoryId": YOUTUBE_CATEGORY,
        },
        "status": {"privacyStatus": YOUTUBE_PRIVACY},
    }

    media = googleapiclient.http.MediaFileUpload(str(file_path), chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()
    return response

# ---- Instagram Reels upload via Graph API (usa video_url apontando para servidor local exposto por ngrok) ----
def start_local_http_server(directory: Path, port=8000):
    """Inicia um http.server simples apontando para 'directory' (process em background)."""
    print(f"🛟 Iniciando servidor HTTP local em {directory} (porta {port})")
    # usa Python -m http.server
    proc = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--directory", str(directory)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    return proc

def start_ngrok_tunnel(port=8000):
    """
    Inicia ngrok e retorna public_url.
    Requer que ngrok esteja disponível no PATH e opcionalmente NGROK_AUTH_TOKEN nas envs.
    """
    print("🚇 Iniciando ngrok...")
    # se NGROK_AUTH_TOKEN foi fornecido, configure
    if NGROK_AUTH_TOKEN:
        try:
            subprocess.run(["ngrok", "authtoken", NGROK_AUTH_TOKEN], check=True)
        except Exception as e:
            print("⚠️ Falha ao definir ngrok authtoken:", e)

    ngrok_proc = subprocess.Popen(["ngrok", "http", str(8000)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(5)  # espera subir
    try:
        tunnels = requests.get("http://127.0.0.1:4040/api/tunnels").json()
        public_url = tunnels["tunnels"][0]["public_url"]
        print("🌍 ngrok público:", public_url)
        return ngrok_proc, public_url
    except Exception as e:
        print("❌ Não foi possível obter a URL do ngrok:", e)
        ngrok_proc.kill()
        return None, None

def instagram_upload_reel(video_public_url: str, caption: str):
    """
    1) Cria container media
    2) Publica o container
    """
    if not IG_ACCESS_TOKEN or not IG_USER_ID:
        raise RuntimeError("IG_ACCESS_TOKEN ou IG_USER_ID não definidos nas envs.")
    # create container
    url = f"https://graph.facebook.com/v20.0/{IG_USER_ID}/media"
    data = {
        "caption": caption,
        "media_type": "REELS",
        "video_url": video_public_url,
        "access_token": IG_ACCESS_TOKEN,
    }
    resp = requests.post(url, data=data).json()
    print("➡️ Instagram container response:", resp)
    if "id" not in resp:
        return resp
    creation_id = resp["id"]

    # aguarda processamento (simples)
    time.sleep(20)

    publish_url = f"https://graph.facebook.com/v20.0/{IG_USER_ID}/media_publish"
    data2 = {"creation_id": creation_id, "access_token": IG_ACCESS_TOKEN}
    publish_resp = requests.post(publish_url, data=data2).json()
    print("➡️ Instagram publish response:", publish_resp)
    return publish_resp

# ---- Caption generator ----
def generate_three_captions():
    base = CAPTION_PREFIX.strip()
    captions = [
        f"{base} Confira este conteúdo incrível! 🔥\n\n#viral #reels #conteudo #dicas #shorts",
        f"{base} Não perca: insights rápidos e diretos. 🚀\n\n#shorts #youtube #reels #aprenda #tutorial",
        f"{base} Post automático — conteúdo pronto para você. ✨\n\n#automação #socialmedia #reels #shorts #conteudo"
    ]
    return captions

# ---- Main flow ----
def pick_next_video():
    if not PENDING_DIR.exists():
        print(f"⚠️ Pasta {PENDING_DIR} não existe.")
        return None
    files = sorted([p for p in PENDING_DIR.iterdir() if p.is_file() and p.suffix.lower() in (".mp4", ".mov", ".avi", ".mkv")])
    if not files:
        print("⚠️ Nenhum vídeo em pending.")
        return None
    return files[0]

def move_to_posted(src: Path):
    POSTED_DIR.mkdir(parents=True, exist_ok=True)
    dst = POSTED_DIR / src.name
    shutil.move(str(src), str(dst))
    print(f"✅ Movido {src.name} -> {dst}")

def main():
    print("🔔 Iniciando processo de postagem (YouTube Shorts + Instagram Reels)")
    # prepara credenciais youtube
    setup_youtube_credentials_from_env()

    video = pick_next_video()
    if not video:
        return

    captions = generate_three_captions()
    caption = random.choice(captions)
    print("📝 Legenda escolhida:\n", caption)

    title = video.stem[:100] + " - Short"  # título simples; ajuste se quiser
    tags = ["shorts", "reels", "automacao"]

    #
