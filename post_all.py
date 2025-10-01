#!/usr/bin/env python3
# post_all.py
"""
Script combinado para postar Reels (Instagram) e Shorts (YouTube).
- Seleciona o primeiro arquivo em videos/pending
- Escolhe 1 de 3 legendas aleatórias (com hashtags)
- Mantém ngrok + http.server para expor o arquivo (Instagram)
- Usa credenciais via variáveis de ambiente (ver README / workflow)
- Move arquivo para videos/posted se pelo menos uma publicação ocorrer
"""

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
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.http
from google.auth.transport.requests import Request

# Configs / paths
PENDING_DIR = "videos/pending"
POSTED_DIR = "videos/posted"
HTTP_SERVER_PORT = int(os.getenv("HTTP_SERVER_PORT", "8000"))
NGROK_AUTHTOKEN = os.getenv("NGROK_AUTHTOKEN")  # recomendado como secret
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")

# YouTube env names (ver workflow)
CLIENT_SECRETS_FILE = "client_secret.json"
TOKEN_FILE = "token.pickle"

# YouTube scopes
YT_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Caption options (3 opções — você pode editar aqui)
CAPTIONS = [
    "🚀 Novo conteúdo no canal! Curtiu? Deixa um like e compartilha. #shorts #conteudo #aprenda",
    "🔥 Dica rápida pra você aplicar hoje — não esquece de salvar! #reels #aprendizado #viral",
    "🎯 Foco e consistência: pequenas ações, grandes resultados. #motivacao #shorts #trabalho"
]

def pick_caption():
    caption = random.choice(CAPTIONS)
    print("Legenda escolhida:", caption)
    return caption

def find_next_video():
    if not os.path.exists(PENDING_DIR):
        print("Pasta pending não encontrada:", PENDING_DIR)
        return None
    files = sorted([f for f in os.listdir(PENDING_DIR) if f.lower().endswith(('.mp4','.mov','.mkv','.avi'))])
    if not files:
        print("Nenhum vídeo em pending.")
        return None
    return os.path.join(PENDING_DIR, files[0])

# ------------------ YouTube helpers (adaptado do upload_youtube.py) ------------------
def setup_youtube_credentials_from_env():
    """
    Espera as variáveis:
      - YOUTUBE_CLIENT_SECRET_JSON (conteúdo do client_secret.json)
      - YOUTUBE_TOKEN_PICKLE (opcional, base64 do token.pickle)
    Cria client_secret.json e token.pickle no runner.
    """
    cs = os.getenv("YOUTUBE_CLIENT_SECRET_JSON")
    tok_b64 = os.getenv("YOUTUBE_TOKEN_PICKLE")  # base64 do pickle (recomendado)
    if not cs:
        raise ValueError("YOUTUBE_CLIENT_SECRET_JSON não definido.")
    with open(CLIENT_SECRETS_FILE, "w") as f:
        f.write(cs)
    print("client_secret.json gravado.")

    if tok_b64:
        token_bytes = base64.b64decode(tok_b64.encode())
        with open(TOKEN_FILE, "wb") as f:
            f.write(token_bytes)
        print("token.pickle gravado a partir de variável.")

def get_authenticated_youtube():
    credentials = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            credentials = pickle.load(f)
        print("Token do YouTube carregado.")
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            print("Atualizando token expirado...")
            credentials.refresh(Request())
        else:
            # No runner interativo: se não houver token.pickle válido, upload falhará.
            raise RuntimeError("Sem token válido do YouTube no runner. Forneça YOUTUBE_TOKEN_PICKLE (base64).")
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(credentials, f)
    return googleapiclient.discovery.build("youtube", "v3", credentials=credentials)

def upload_to_youtube(file_path, title, description, tags=None, category_id="22", privacy="public"):
    print("Iniciando upload para YouTube:", file_path)
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
            print(f"Upload progresso: {int(status.progress() * 100)}%")
        if response:
            break
    print("YouTube upload concluído ID:", response.get("id"))
    return response

# ------------------ Instagram helpers (adaptado de upload_instagram.py) ------------------
def start_ngrok_and_get_public_url():
    """
    Inicia ngrok (necessário ter ngrok no PATH). Usa NGROK_AUTHTOKEN se fornecido.
    Retorna a URL pública.
    """
    # se authtoken, configura
    if NGROK_AUTHTOKEN:
        print("Configuring ngrok authtoken...")
        subprocess.run(["ngrok", "authtoken", NGROK_AUTHTOKEN], check=False)

    # inicia ngrok http server apontando para porta do http.server
    print("Iniciando ngrok...")
    ngrok_proc = subprocess.Popen(["ngrok", "http", str(HTTP_SERVER_PORT)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # aguarda ngrok subir
    time.sleep(5)
    try:
        tunnel_info = requests.get("http://127.0.0.1:4040/api/tunnels").json()
        public_url = tunnel_info["tunnels"][0]["public_url"]
        print("ngrok público:", public_url)
        return ngrok_proc, public_url
    except Exception as e:
        print("Erro ao obter URL do ngrok:", e)
        ngrok_proc.kill()
        raise

def upload_instagram_reel(video_public_url, caption):
    url = f"https://graph.facebook.com/v20.0/{IG_USER_ID}/media"
    data = {
        "caption": caption,
        "media_type": "REELS",
        "video_url": video_public_url,
        "access_token": IG_ACCESS_TOKEN
    }
    resp = requests.post(url, data=data).json()
    return resp

def publish_instagram(container_id):
    url = f"https://graph.facebook.com/v20.0/{IG_USER_ID}/media_publish"
    data = {
        "creation_id": container_id,
        "access_token": IG_ACCESS_TOKEN
    }
    resp = requests.post(url, data=data).json()
    return resp

# ------------------ Runner ------------------
def main():
    # passo 0: valida envs mínimas para IG (YouTube é opcional se for apenas instagram)
    if not os.path.exists(PENDING_DIR):
        print("Pasta pending não existe. Criando...")
        os.makedirs(PENDING_DIR, exist_ok=True)

    video_path = find_next_video()
    if not video_path:
        print("Nada a postar. Encerrando.")
        return

    caption = pick_caption()

    # inicia http.server no PENDING_DIR
    print("Iniciando servidor HTTP local...")
    http_proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(HTTP_SERVER_PORT), "--directory", PENDING_DIR],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1)

    ngrok_proc = None
    public_url = None
    ig_success = False
    yt_success = False

    try:
        # inicia ngrok e pega URL pública
        ngrok_proc, public_url = start_ngrok_and_get_public_url()
        video_file = os.path.basename(video_path)
        video_public_url = f"{public_url}/{video_file}"
        print("URL público do vídeo:", video_public_url)

        # 1) Tentar postar no Instagram (se credenciais presentes)
        if IG_ACCESS_TOKEN and IG_USER_ID:
            print("Tentando upload para Instagram Reels...")
            up_resp = upload_instagram_reel(video_public_url, caption)
            print("Resposta upload IG:", up_resp)
            if "id" in up_resp:
                container_id = up_resp["id"]
                print("Aguardando processamento (30s)...")
                time.sleep(30)
                pub_resp = publish_instagram(container_id)
                print("Resposta publish IG:", pub_resp)
                if "id" in pub_resp:
                    print("Instagram: publicado com sucesso!")
                    ig_success = True
                else:
                    print("Instagram: erro ao publicar:", pub_resp)
            else:
                print("Instagram: erro no upload:", up_resp)
        else:
            print("IG_ACCESS_TOKEN ou IG_USER_ID não fornecido; pulando Instagram.")

        # 2) Tentar postar no YouTube (se credenciais presentes)
        if os.getenv("YOUTUBE_CLIENT_SECRET_JSON"):
            print("Tentando upload para YouTube...")
            try:
                # prepara credenciais no runner
                setup_youtube_credentials_from_env()
                # titulo/descricao simples
                title = os.path.splitext(os.path.basename(video_path))[0][:100]
                desc = caption + "\n\nPublicado automaticamente."
                upload_resp = upload_to_youtube(video_path, title=title, description=desc, tags=["shorts","automacao"])
                if upload_resp and "id" in upload_resp:
                    print("YouTube: publicado com ID:", upload_resp["id"])
                    yt_success = True
                else:
                    print("YouTube: resposta inesperada:", upload_resp)
            except Exception as e:
                print("YouTube upload falhou:", e)
        else:
            print("YOUTUBE_CLIENT_SECRET_JSON não fornecido; pulando YouTube.")

    finally:
        # encerra ngrok e http.server
        if ngrok_proc:
            try:
                ngrok_proc.kill()
            except:
                pass
        if http_proc:
            try:
                http_proc.kill()
            except:
                pass

    # Se pelo menos um upload deu certo, move o arquivo
    if ig_success or yt_success:
        os.makedirs(POSTED_DIR, exist_ok=True)
        dst = os.path.join(POSTED_DIR, os.path.basename(video_path))
        try:
            shutil.move(video_path, dst)
            print(f"Vídeo movido para {dst}")
        except Exception as e:
            print("Erro ao mover arquivo:", e)
    else:
        print("Nenhuma publicação teve sucesso — o arquivo NÃO foi movido.")

if __name__ == "__main__":
    main()
