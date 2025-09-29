import os
import requests
import time
import shutil
import subprocess

ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")
CAPTION = "🚀 Postagem automática via API"

PENDING_DIR = "videos/pending"
POSTED_DIR = "videos/posted"

def start_ngrok():
    # Inicia ngrok apontando para o servidor HTTP local na porta 8000
    ngrok = subprocess.Popen(["ngrok", "http", "8000"], stdout=subprocess.PIPE)
    time.sleep(5)  # espera o ngrok subir

    # Pega a URL pública do ngrok pela API local
    url = requests.get("http://127.0.0.1:4040/api/tunnels").json()["tunnels"][0]["public_url"]
    return url

def upload_reels(video_url):
    url = f"https://graph.facebook.com/v20.0/{IG_USER_ID}/media"
    data = {
        'caption': CAPTION,
        'media_type': 'REELS',
        'video_url': video_url,
        'access_token': ACCESS_TOKEN
    }
    return requests.post(url, data=data).json()

def publish_reels(container_id):
    url = f"https://graph.facebook.com/v20.0/{IG_USER_ID}/media_publish"
    data = {
        'creation_id': container_id,
        'access_token': ACCESS_TOKEN
    }
    return requests.post(url, data=data).json()

if __name__ == "__main__":
    files = sorted(os.listdir(PENDING_DIR))
    if not files:
        print("⚠️ Nenhum vídeo para postar.")
        exit(0)

    video_file = files[0]
    print(f"➡️ Preparando vídeo: {video_file}")

    # inicia servidor HTTP local para servir os vídeos
    subprocess.Popen(["python3", "-m", "http.server", "8000", "--directory", PENDING_DIR])
    base_url = start_ngrok()
    video_url = f"{base_url}/{video_file}"
    print(f"🌍 URL pública gerada: {video_url}")

    upload_resp = upload_reels(video_url)
    print("Upload response:", upload_resp)

    if "id" in upload_resp:
        container_id = upload_resp["id"]

        print("⏳ Aguardando processamento...")
        time.sleep(30)

        publish_resp = publish_reels(container_id)
        print("Publish response:", publish_resp)

        if "id" in publish_resp:
            src = os.path.join(PENDING_DIR, video_file)
            dst = os.path.join(POSTED_DIR, video_file)
            shutil.move(src, dst)
            print(f"✅ Vídeo {video_file} postado e movido para {POSTED_DIR}")
        else:
            print("❌ Erro ao publicar:", publish_resp)
    else:
        print("❌ Erro no upload:", upload_resp)
