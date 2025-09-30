from TikTokApi import TikTokApi
import os
import sys

# Variáveis de ambiente definidas no GitHub Actions
SESSIONID = os.getenv("TIKTOK_SESSIONID")
VIDEO_PATH = os.getenv("VIDEO_PATH")
DESCRIPTION = os.getenv("DESCRIPTION", "Automated upload")

if not SESSIONID:
    print("[ERROR] TIKTOK_SESSIONID environment variable is required.")
    sys.exit(1)

if not VIDEO_PATH or not os.path.exists(VIDEO_PATH):
    print(f"[ERROR] Video file not found: {VIDEO_PATH}")
    sys.exit(1)

try:
    api = TikTokApi.get_instance()
    api.login(sessionid=SESSIONID)

    print(f"[INFO] Uploading video: {VIDEO_PATH}")
    upload = api.upload_video(VIDEO_PATH, description=DESCRIPTION)
    
    share_url = upload.get("item", {}).get("share_url", None)
    if share_url:
        print(f"[SUCCESS] Video uploaded! Link: {share_url}")
    else:
        print("[ERROR] Upload completed but no share_url returned.")

except Exception as e:
    print("[ERROR] Upload failed:", e)
    sys.exit(1)
