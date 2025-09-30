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
    s = random.uniform(a, b)
    print(f"[wait] sleeping {s:.2f}s")
    time.sleep(s)


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
    print("[driver] starting Chrome driver (webdriver-manager)")
    options = Options()
    if HEADLESS:
        print("[driver] running in headless mode (env HEADLESS=true)")
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
    else:
        print("[driver] running with visible browser (HEADLESS=false)")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=pt-BR")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
    driver.set_window_size(1280, 800)
    print("[driver] started")
    return driver


def login_tiktok(driver):
    print("[login] navigating to login page")
    driver.get("https://www.tiktok.com/login")

    try:
        WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    except Exception as e:
        print("[login] page load timeout", e)
        save_debug(driver, "login_page_load_error")
        raise

    try:
        # Tentar abrir aba de "Email / Username"
        try:
            btn = driver.find_element(
                By.XPATH,
                "//button[contains(., 'Use phone') or contains(., 'email') or contains(., 'username')]"
            )
            print("[login] clicking 'Use phone / email / username' button")
            btn.click()
            rnd_sleep(1, 2)
        except Exception:
            print("[login] no 'Use phone / email' button found (maybe already on form)")

        # Forçar selecionar aba de Email/Username se existir
        try:
            email_tab = driver.find_element(By.XPATH, "//div[contains(text(),'Email') or contains(text(),'Username')]")
            print("[login] selecting Email/Username tab")
            email_tab.click()
            rnd_sleep(1, 2)
        except Exception:
            print("[login] no explicit Email/Username tab")

        # Campo de usuário
        email_input = None
        try:
            email_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "input[name='username'], input[name='email'], input[placeholder*='Email'], input[placeholder*='usuário']"
                ))
            )
            print("[login] found username/email input")
            email_input.clear()
            email_input.send_keys(USERNAME)
            rnd_sleep(0.5, 1.2)
        except Exception as e:
            print("[login] username/email input not found:", e)
            save_debug(driver, "login_no_username")
            raise

        # Campo de senha
        try:
            pwd_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "input[type='password'], input[autocomplete='current-password']"
                ))
            )
            print("[login] found password input")
            pwd_input.clear()
            pwd_input.send_keys(PASSWORD)
            rnd_sleep(0.5, 1.2)
        except Exception as e:
            print("[login] password input not found:", e)
            save_debug(driver, "login_no_password")
            raise

        # Botão de login
        try:
            possible_buttons = driver.find_elements(By.XPATH, "//button")
            clicked = False
            for b in possible_buttons:
                text = (b.text or "").strip().lower()
                if any(k in text for k in ["log in", "login", "entrar", "sign in"]):
                    print(f"[login] clicking button with text: '{b.text}'")
                    b.click()
                    clicked = True
                    break
            if not clicked:
                print("[login] no login button detected by text; pressing Enter on password field")
                pwd_input.send_keys("\n")
        except Exception as e:
            print("[login] submit attempt failed:", e)

        print("[login] waiting for post-login state (up to 30s)...")
        try:
            WebDriverWait(driver, 30).until(EC.url_contains("tiktok.com"))
            rnd_sleep(2, 4)
            print("[login] login flow likely complete. Current URL:", driver.current_url)
        except Exception:
            print("[login] didn't detect redirect; saving debug")
            save_debug(driver, "login_maybe_needs_action")
            raise RuntimeError("Login may need manual intervention (2FA/captcha). See debug artifacts.")

    except Exception as e:
        print("[login] exception during login flow:", e)
        raise


def upload_one_video(driver, video_path):
    print(f"[upload] starting upload for {video_path}")
    try:
        driver.get("https://www.tiktok.com/upload?lang=pt")
        WebDriverWait(driver, TIMEOUT).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        rnd_sleep(2, 4)

        # Input de arquivo
        try:
            file_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="file"]'))
            )
            print("[upload] found file input, sending file")
            abs_path = os.path.abspath(video_path)
            file_input.send_keys(abs_path)
        except Exception as e:
            print("[upload] file input not found:", e)
            save_debug(driver, "upload_no_file_input")
            raise

        # Esperar preview
        try:
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class,'video-preview') or contains(@class,'upload')]"))
            )
            print("[upload] preview/processing element detected")
        except Exception:
            print("[upload] preview not detected; saving debug")
            save_debug(driver, "upload_no_preview")

        rnd_sleep(3, 6)

        # Legenda
        try:
            caption_area = driver.find_element(
                By.XPATH,
                "//textarea[contains(@placeholder,'legenda') or contains(@placeholder,'caption') or @aria-label='Write a caption']"
            )
            caption_area.clear()
            caption_area.send_keys("Automated upload - teste")
            print("[upload] wrote caption")
            rnd_sleep(0.5, 1.2)
        except Exception:
            print("[upload] caption not found (non-fatal)")

        # Botão de publicar
        try:
            buttons = driver.find_elements(By.XPATH, "//button")
            for b in buttons:
                t = (b.text or "").strip().lower()
                if any(k in t for k in ["post", "postar", "publish", "publicar"]):
                    print(f"[upload] clicking publish button with text: '{b.text}'")
                    b.click()
                    break
            else:
                print("[upload] publish button not found by text; fallback")
                publish = driver.find_element(By.XPATH, "//button[@aria-label='Post' or @aria-label='Upload']")
                publish.click()
        except Exception as e:
            print("[upload] clicking publish failed:", e)
            save_debug(driver, "upload_no_publish_button")
            raise

        # Confirmação
        try:
            WebDriverWait(driver, 60).until(
                EC.any_of(
                    EC.url_contains("/post/"),
                    EC.presence_of_element_located((By.XPATH, "//div[contains(text(),'Publicado') or contains(text(),'Posted') or contains(text(),'success')]"))
                )
            )
            print("[upload] seems posted (heuristic triggered).")
        except Exception:
            print("[upload] no clear confirmation; saving debug")
            save_debug(driver, "upload_no_confirmation")

        print(f"[upload] finished upload attempt for {video_path}")
    except Exception as e:
        print("[upload] exception:", e)
        save_debug(driver, "upload_exception")
        raise


def main():
    if not USERNAME or not PASSWORD:
        print("[error] TIKTOK_USERNAME and TIKTOK_PASSWORD env vars required.")
        return

    print("[main] starting process")
    driver = start_driver()
    try:
        try:
            login_tiktok(driver)
        except Exception as e:
            print("[main] login flow error:", e)
            driver.quit()
            return

        videos = [os.path.join(VIDEO_FOLDER, f) for f in sorted(os.listdir(VIDEO_FOLDER)) if f.lower().endswith(".mp4")]
        print(f"[main] found {len(videos)} mp4 files in {VIDEO_FOLDER}")

        for idx, v in enumerate(videos, 1):
            print(f"[main] uploading {idx}/{len(videos)}: {v}")
            try:
                upload_one_video(driver, v)
            except Exception as e:
                print(f"[main] upload failed for {v}: {e}")
            rnd_sleep(20, 60)
    finally:
        print("[main] quitting driver")
        try:
            driver.quit()
        except Exception:
            pass
    print("[main] done")


if __name__ == "__main__":
    main()
