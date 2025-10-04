import os
import requests
import time
import subprocess
import json

ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")

PENDING_DIR = "videos/pending"


def start_ngrok():
    """Inicia ngrok e retorna a URL pública"""
    ngrok = subprocess.Popen(["ngrok", "http", "8000"], stdout=subprocess.PIPE)
    time.sleep(5)
    url = requests.get("http://127.0.0.1:4040/api/tunnels").json()["tunnels"][0]["public_url"]
    return url


def get_metadata(video_file):
    if os.path.exists("metadata.json"):
        with open("metadata.json", "r", encoding="utf-8") as f:
            metadata = json.load(f)
        return metadata.get(video_file, {})
    return {}


def upload_reels(video_url, caption):
    url = f"https://graph.facebook.com/v20.0/{IG_USER_ID}/media"
    data = {
        "caption": caption,
        "media_type": "REELS",
        "video_url": video_url,
        "access_token": ACCESS_TOKEN,
    }
    return requests.post(url, data=data).json()


def check_status(container_id):
    """Verifica o status do processamento do vídeo"""
    status_url = f"https://graph.facebook.com/v20.0/{container_id}?fields=status_code&access_token={ACCESS_TOKEN}"
    response = requests.get(status_url).json()
    return response.get("status_code", "")


def publish_reels(container_id):
    url = f"https://graph.facebook.com/v20.0/{IG_USER_ID}/media_publish"
    data = {"creation_id": container_id, "access_token": ACCESS_TOKEN}
    return requests.post(url, data=data).json()


if __name__ == "__main__":
    if not os.path.exists(PENDING_DIR):
        print(f"⚠️ Pasta {PENDING_DIR} não existe.")
        exit(0)

    files = sorted(os.listdir(PENDING_DIR))
    print("📂 Arquivos encontrados:", files)

    if not files:
        print("⚠️ Nenhum vídeo para postar.")
        exit(0)

    video_file = files[0]
    video_path = os.path.join(PENDING_DIR, video_file)

    if not os.path.isfile(video_path):
        print(f"❌ Arquivo não encontrado: {video_path}")
        exit(1)

    meta = get_metadata(video_file)
    caption = meta.get("description", "🚀 Postagem automática via API")

    print(f"➡️ Preparando vídeo: {video_file} | Legenda: {caption}")

    subprocess.Popen(["python3", "-m", "http.server", "8000", "--directory", PENDING_DIR])
    base_url = start_ngrok()
    video_url = f"{base_url}/{video_file}"
    print(f"🌍 URL pública: {video_url}")

    upload_resp = upload_reels(video_url, caption)
    print("Upload response:", upload_resp)

    if "id" in upload_resp:
        container_id = upload_resp["id"]
        print("⏳ Aguardando processamento...")

        # Espera até status FINISHED
        for _ in range(30):
            status = check_status(container_id)
            print(f"🔁 Status atual: {status}")
            if status == "FINISHED":
                break
            time.sleep(10)
        else:
            print("❌ Tempo limite atingido, vídeo não processado.")
            exit(1)

        publish_resp = publish_reels(container_id)
        print("Publish response:", publish_resp)

        if "id" in publish_resp:
            print(f"✅ Vídeo {video_file} postado com sucesso no Instagram.")
        else:
            print("❌ Erro ao publicar:", publish_resp)
    else:
        print("❌ Erro no upload:", upload_resp)
