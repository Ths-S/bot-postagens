import os
import requests
import time
import shutil
import subprocess
import json

ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")
CAPTION = "🚀 Postagem automática via API"

PENDING_DIR = "videos/pending"
POSTED_DIR = "videos/posted"


def start_ngrok():
    """Inicia ngrok e retorna a URL pública para o servidor local."""
    try:
        ngrok = subprocess.Popen(["ngrok", "http", "8000"], stdout=subprocess.PIPE)
        time.sleep(5)  # tempo para ngrok subir

        resp = requests.get("http://127.0.0.1:4040/api/tunnels").json()
        tunnels = resp.get("tunnels", [])
        if not tunnels:
            raise RuntimeError("Nenhum túnel ngrok encontrado.")

        return tunnels[0]["public_url"]
    except Exception as e:
        print("❌ Erro ao iniciar ngrok:", e)
        return None


def upload_reels(video_url):
    """Cria o contêiner de upload do Reels com video_url."""
    url = f"https://graph.facebook.com/v20.0/{IG_USER_ID}/media"
    data = {
        "caption": CAPTION,
        "media_type": "REELS",
        "video_url": video_url,
        "access_token": ACCESS_TOKEN
    }
    resp = requests.post(url, data=data).json()
    return resp


def publish_reels(container_id):
    """Publica o Reels já enviado."""
    url = f"https://graph.facebook.com/v20.0/{IG_USER_ID}/media_publish"
    data = {
        "creation_id": container_id,
        "access_token": ACCESS_TOKEN
    }
    resp = requests.post(url, data=data).json()
    return resp


if __name__ == "__main__":
    if not os.path.exists(PENDING_DIR):
        print(f"⚠️ Pasta {PENDING_DIR} não existe.")
        exit(0)

    files = sorted(os.listdir(PENDING_DIR))  # ordem alfabética
    print("📂 Arquivos encontrados em pending:", files)

    if not files:
        print("⚠️ Nenhum vídeo para postar.")
        exit(0)

    # pega o primeiro vídeo da lista
    video_file = files[0]
    video_path = os.path.join(PENDING_DIR, video_file)

    if not os.path.isfile(video_path):
        print(f"❌ Arquivo não encontrado: {video_path}")
        exit(1)

    print(f"➡️ Preparando vídeo: {video_file}")
    print(f"📍 Caminho absoluto: {os.path.abspath(video_path)}")

    # inicia servidor HTTP local para servir o vídeo
    subprocess.Popen(["python3", "-m", "http.server", "8000", "--directory", PENDING_DIR])

    base_url = start_ngrok()
    if not base_url:
        print("❌ Não foi possível iniciar ngrok.")
        exit(1)

    video_url = f"{base_url}/{video_file}"
    print(f"🌍 URL pública gerada: {video_url}")

    upload_resp = upload_reels(video_url)
    print("📡 Upload response:", json.dumps(upload_resp, indent=2))

    if "id" not in upload_resp:
        print("❌ Erro no upload:", upload_resp)
        exit(1)

    container_id = upload_resp["id"]

    print("⏳ Aguardando processamento...")
    time.sleep(30)

    publish_resp = publish_reels(container_id)
    print("📡 Publish response:", json.dumps(publish_resp, indent=2))

    if "id" in publish_resp:
        os.makedirs(POSTED_DIR, exist_ok=True)
        shutil.move(video_path, os.path.join(POSTED_DIR, video_file))
        print(f"✅ Vídeo {video_file} postado e movido para {POSTED_DIR}")
    else:
        print("❌ Erro ao publicar:", publish_resp)
        exit(1)
