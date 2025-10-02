import os
import requests
import time
import shutil

ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")
CAPTION = "🚀 Postagem automática via API"

PENDING_DIR = "videos/pending"
POSTED_DIR = "videos/posted"

def upload_reels(video_path):
    """Faz upload direto do vídeo para o Instagram (Resumable Upload)."""
    file_size = os.path.getsize(video_path)

    # Passo 1: criar contêiner de upload
    url = f"https://graph-video.facebook.com/v20.0/{IG_USER_ID}/media"
    params = {
        "upload_phase": "start",
        "access_token": ACCESS_TOKEN,
        "media_type": "REELS",
        "caption": CAPTION,
    }
    resp = requests.post(url, data=params).json()
    print("📡 Start response:", resp)

    if "upload_session_id" not in resp:
        return None

    session_id = resp["upload_session_id"]
    video_id = resp.get("video_id")

    # Passo 2: upload do arquivo em chunks
    with open(video_path, "rb") as f:
        chunk = f.read()
        params = {
            "upload_phase": "transfer",
            "access_token": ACCESS_TOKEN,
            "upload_session_id": session_id,
            "start_offset": 0,
        }
        files = {"video_file_chunk": chunk}
        resp2 = requests.post(url, data=params, files=files).json()
        print("📡 Transfer response:", resp2)

    # Passo 3: finalizar upload
    params = {
        "upload_phase": "finish",
        "access_token": ACCESS_TOKEN,
        "upload_session_id": session_id,
    }
    resp3 = requests.post(url, data=params).json()
    print("📡 Finish response:", resp3)

    return video_id


def publish_reels(video_id):
    """Publica o vídeo já enviado no feed de Reels."""
    url = f"https://graph.facebook.com/v20.0/{IG_USER_ID}/media_publish"
    data = {
        "creation_id": video_id,
        "access_token": ACCESS_TOKEN,
    }
    return requests.post(url, data=data).json()


if __name__ == "__main__":
    if not os.path.exists(PENDING_DIR):
        print(f"⚠️ Pasta {PENDING_DIR} não existe.")
        exit(0)

    files = sorted(os.listdir(PENDING_DIR))  # ordem A-Z
    print("📂 Arquivos encontrados em pending:", files)

    if not files:
        print("⚠️ Nenhum vídeo para postar.")
        exit(0)

    video_file = files[0]  # pega o primeiro
    video_path = os.path.join(PENDING_DIR, video_file)

    if not os.path.isfile(video_path):
        print(f"❌ Arquivo não encontrado: {video_path}")
        exit(1)

    print(f"➡️ Preparando upload do vídeo: {video_file}")

    video_id = upload_reels(video_path)
    if not video_id:
        print("❌ Falha no upload do vídeo.")
        exit(1)

    print("⏳ Aguardando processamento do vídeo...")
    time.sleep(30)

    publish_resp = publish_reels(video_id)
    print("📡 Publish response:", publish_resp)

    if "id" in publish_resp:
        os.makedirs(POSTED_DIR, exist_ok=True)
        shutil.move(video_path, os.path.join(POSTED_DIR, video_file))
        print(f"✅ Vídeo {video_file} postado e movido para {POSTED_DIR}")
    else:
        print("❌ Erro ao publicar:", publish_resp)
