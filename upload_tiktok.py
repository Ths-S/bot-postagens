# upload_tiktok.py
# Requer: pip install selenium webdriver-manager

import os
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options

VIDEO_FOLDER = "videos"
USERNAME = os.getenv("TIKTOK_USERNAME")
PASSWORD = os.getenv("TIKTOK_PASSWORD")
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"
TIMEOUT = 30

def rnd_sleep(a=1.0, b=3.0):
    time.sleep(random.uniform(a, b))

def save_debug(driver, name_prefix):
    try:
        timestamp = int(time.time())
        html = driver.page_source
        with open(f"debug_{name_prefix}_{timestamp}.html", "w", encoding="utf-8") as f:
            f.write(html)
        screenshot = f"debug_{name_prefix}_{timestamp}.png"
        driver.save_screenshot(screenshot)
        print(f"[debug] saved {screenshot} and html")
    except Exception as e:
        print("[debug] failed to save debug artifacts:", e)

def start_driver():
    options = Options()
    if HEADLESS:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=pt-BR")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
    driver.set_window_size(1280, 800)
    return driver

def login_tiktok(driver):
    driver.get("https://www.tiktok.com/login/phone-or-email/email")
    WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    rnd_sleep(2, 4)

    try:
        # Campo email/username
        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='Email']"))
        )
        email_input.clear()
        email_input.send_keys(USERNAME)
        rnd_sleep(1, 2)

        pwd_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']"))
        )
        pwd_input.clear()
        pwd_input.send_keys(PASSWORD)
        rnd_sleep(1, 2)

        # Botão login
        login_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Log in') or contains(., 'Entrar')]"))
        )
        login_btn.click()
        rnd_sleep(5, 8)

        # Espera pós-login
        WebDriverWait(driver, 30).until(EC.url_contains("tiktok.com"))
        print("[login] login completed, current URL:", driver.current_url)
    except Exception as e:
        print("[login] failed:", e)
        save_debug(driver, "login_fail")
        raise

def upload_one_video(driver, video_path):
    driver.get("https://www.tiktok.com/tiktokstudio/upload?from=creator_center")
    WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    rnd_sleep(2, 4)

    try:
        # Input file
        file_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
        )
        abs_path = os.path.abspath(video_path)
        file_input.send_keys(abs_path)
        rnd_sleep(5, 8)

        # Legenda
        try:
            caption_area = driver.find_element(By.XPATH, "//textarea[contains(@placeholder,'caption') or contains(@placeholder,'legenda')]")
            caption_area.clear()
            caption_area.send_keys("Automated upload - teste")
        except:
            print("[upload] caption not found (continuing)")

        # Botão publicar
        publish_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Post') or contains(., 'Publicar')]"))
        )
        publish_btn.click()
        rnd_sleep(5, 10)
        print(f"[upload] video {video_path} uploaded")
    except Exception as e:
        print(f"[upload] failed for {video_path}: {e}")
        save_debug(driver, "upload_fail")

def get_all_videos(folder):
    video_files = []
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(".mp4"):
                video_files.append(os.path.join(root, f))
    return sorted(video_files)

def main():
    if not USERNAME or not PASSWORD:
        print("[error] TIKTOK_USERNAME and TIKTOK_PASSWORD env vars required.")
        return

    print("Current dir:", os.getcwd())
    print("Video folder exists:", os.path.exists(VIDEO_FOLDER))
    if os.path.exists(VIDEO_FOLDER):
        print("Files in video folder:", os.listdir(VIDEO_FOLDER))

    driver = start_driver()
    try:
        login_tiktok(driver)

        videos = get_all_videos(VIDEO_FOLDER)
        print(f"[main] found {len(videos)} mp4 files in {VIDEO_FOLDER}")

        for v in videos:
            try:
                upload_one_video(driver, v)
            except Exception as e:
                print(f"[main] upload failed for {v}: {e}")
            rnd_sleep(20, 60)
    finally:
        driver.quit()
        print("[main] done")

if __name__ == "__main__":
    main()
