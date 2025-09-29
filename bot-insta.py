import os
import requests
import time
import shutil

ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")
BASE_URL = "https://Ths-S.github.io/bot-postagens/videos/pending/"  # ajuste para seu repo

CAPTION = "🚀 Postagem automática via API"
PENDING_DIR = "videos/pending"
POSTED_DIR = "videos/posted"

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
    # pega o primeiro vídeo na pasta
    files = sorted(os.listdir(PENDING_DIR))
    if not files:
        print("⚠️ Nenhum vídeo para postar.")
        exit(0)

    video_file = files[0]
    video_url = BASE_URL + video_file
    print(f"➡️ Preparando vídeo: {video_file}")

    # cria container
    upload_resp = upload_reels(video_url)
    print("Upload response:", upload_resp)

    if "id" in upload_resp:
        container_id = upload_resp["id"]

        print("⏳ Aguardando processamento...")
        time.sleep(30)

        publish_resp = publish_reels(container_id)
        print("Publish response:", publish_resp)

        if "id" in publish_resp:
            # mover arquivo para posted/
            src = os.path.join(PENDING_DIR, video_file)
            dst = os.path.join(POSTED_DIR, video_file)
            shutil.move(src, dst)
            print(f"✅ Vídeo {video_file} postado e movido para {POSTED_DIR}")
        else:
            print("❌ Erro ao publicar:", publish_resp)
    else:
        print("❌ Erro no upload:", upload_resp)
