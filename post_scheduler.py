#!/usr/bin/env python3
"""
post_scheduler.py
Script orquestrador para postar o próximo vídeo em videos/pending como
- YouTube Shorts (usando upload_youtube.py)
- Instagram Reels (usando upload_instagram.py)

Uso:
  - Configure variáveis de ambiente (ver README abaixo)
  - Agende via cron para rodar às 06:00, 14:00, 22:00 (ou execute manualmente)

Observações:
  - O script NÃO re-encoda o arquivo; usa o vídeo original (isso preserva qualidade).
  - Se preferir testar sem postar, defina dry_run: true no YAML.
"""

import os
import sys
import yaml
import random
import time
import shutil
import subprocess
from pathlib import Path

# importa das suas implementações
# upload_youtube.py deve estar no mesmo diretório e expor setup_credentials_files e upload_video
# upload_instagram.py deve estar no mesmo diretório e expor start_ngrok, upload_reels, publish_reels
try:
    import upload_youtube as youtube_module
except Exception as e:
    youtube_module = None
    # we'll handle later

try:
    import upload_instagram as instagram_module
except Exception as e:
    instagram_module = None

# --- helpers ---
def load_config(path="post_schedule.yml"):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config YAML não encontrado: {path}")
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg

def find_next_video(pending_dir):
    p = Path(pending_dir)
    if not p.exists():
        return None
    files = [f for f in sorted(p.iterdir()) if f.is_file() and f.suffix.lower() in (".mp4", ".mov", ".mkv", ".avi")]
    return files[0] if files else None

def start_simple_http_server(directory, port=8000):
    # start a simple HTTP server in background serving `directory`
    proc = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--directory", directory],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # give it a moment
    time.sleep(1.5)
    return proc

def stop_process(proc):
    try:
        proc.terminate()
    except Exception:
        pass

def move_file(src, dst_dir):
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, os.path.basename(src))
    shutil.move(src, dst)
    return dst

# --- main flow ---
def main():
    cfg = load_config()
    pending_dir = cfg.get("pending_dir", "videos/pending")
    posted_dir = cfg.get("posted_dir", "videos/posted")
    dry_run = cfg.get("dry_run", False)
    require_both = cfg.get("require_both_platforms_success", False)

    video = find_next_video(pending_dir)
    if not video:
        print("⚠️  Nenhum vídeo em pending. Saindo.")
        return

    video_path = str(video.resolve())
    print(f"🎬 Próximo vídeo: {video_path}")

    # escolhe legenda
    captions = cfg.get("captions", [])
    if not captions:
        caption = ""
    else:
        caption = random.choice(captions)
    print(f"📝 Legenda escolhida: {caption}")

    # --- YouTube upload ---
    youtube_ok = False
    youtube_resp = None
    if dry_run:
        print("🧪 DRY RUN: pulando upload real para YouTube")
        youtube_ok = True
    else:
        if youtube_module is None:
            print("❌ Módulo upload_youtube.py não encontrado/importado.")
        else:
            try:
                # prepara credenciais (se o seu upload_youtube.py tiver esse método)
                if hasattr(youtube_module, "setup_credentials_files"):
                    youtube_module.setup_credentials_files()
                # title/description
                title = caption if len(caption) <= 100 else caption[:95] + "..."
                description = caption + "\n\nPublicado automaticamente."
                print("🚀 Enviando para YouTube...")
                resp = youtube_module.upload_video(file_path=video_path,
                                                   title=title,
                                                   description=description,
                                                   tags=["shorts", "reels", "automacao"],
                                                   category_id=cfg.get("youtube", {}).get("category_id", "22"),
                                                   privacy=cfg.get("youtube", {}).get("privacy", "public"),
                                                   dry_run=False)
                youtube_resp = resp
                if isinstance(resp, dict) and ("id" in resp or resp.get("id") is not None):
                    youtube_ok = True
                    print("✅ YouTube OK. ID:", resp.get("id"))
                else:
                    print("❌ YouTube resposta inesperada:", resp)
            except Exception as e:
                print("❌ Erro ao enviar YouTube:", e)

    # --- Instagram upload ---
    instagram_ok = False
    instagram_resp = None
    if dry_run:
        print("🧪 DRY RUN: pulando upload real para Instagram")
        instagram_ok = True
    else:
        if instagram_module is None:
            print("❌ Módulo upload_instagram.py não encontrado/importado.")
        else:
            try:
                # 1) start local HTTP server to serve the pending_dir (so ngrok can fetch it)
                print("🌐 Iniciando servidor HTTP local para o diretório pending...")
                server_proc = start_simple_http_server(pending_dir, port=8000)
                # 2) start ngrok and get public url (upload_instagram.start_ngrok lê local 4040)
                if hasattr(instagram_module, "start_ngrok"):
                    print("🔌 Iniciando ngrok e pegando URL pública...")
                    base_url = instagram_module.start_ngrok()
                else:
                    raise RuntimeError("função start_ngrok não encontrada em upload_instagram.py")
                # 3) build video url and call instagram upload/publish
                video_file = os.path.basename(video_path)
                video_url = f"{base_url}/{video_file}"
                print("➡️ URL do vídeo:", video_url)
                upload_resp = instagram_module.upload_reels(video_url)
                print("📤 Resposta upload (container):", upload_resp)
                container_id = upload_resp.get("id") or upload_resp.get("container_id")
                if not container_id:
                    print("❌ Não recebeu container_id do Instagram. Resposta:", upload_resp)
                else:
                    print("⏳ Aguardando processamento do container do Instagram...")
                    time.sleep(20)
                    publish_resp = instagram_module.publish_reels(container_id)
                    print("📣 Resposta de publish:", publish_resp)
                    if isinstance(publish_resp, dict) and ("id" in publish_resp or publish_resp.get("id") is not None):
                        instagram_ok = True
                        instagram_resp = publish_resp
                        print("✅ Instagram OK. ID:", publish_resp.get("id"))
                    else:
                        print("❌ Instagram publish erro/resposta:", publish_resp)

                # 4) cleanup: stop HTTP server and try to stop ngrok process (if started by module we can't reliably kill it)
                stop_process(server_proc)
            except Exception as e:
                print("❌ Erro ao enviar Instagram:", e)

    # --- mover arquivo se apropriado ---
    should_move = False
    if cfg.get("move_after_post", True):
        if require_both:
            should_move = (youtube_ok and instagram_ok)
        else:
            should_move = (youtube_ok or instagram_ok)

    if should_move:
        try:
            dst = move_file(video_path, posted_dir)
            print(f"📁 Arquivo movido para {dst}")
        except Exception as e:
            print("❌ Erro ao mover arquivo:", e)
    else:
        print("ℹ️ Arquivo NÃO movido (condição de mover não satisfeita). YouTube ok:", youtube_ok, "Instagram ok:", instagram_ok)

if __name__ == "__main__":
    main()
