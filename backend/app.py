import os
from flask import Flask, request, send_file
from flask_cors import CORS
import pandas as pd
import subprocess
import tempfile
import json
import requests
from urllib.parse import urlparse

# ✅ Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time

app = Flask(__name__)

CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=True
)

# -------------------------------
# Extract platform + username
# -------------------------------
def extract_platform_username(url):

    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path.strip("/")

    if "facebook.com" in domain:
        if "profile.php" in url:
            import urllib.parse
            query = urllib.parse.parse_qs(parsed.query)
            if "id" in query:
                return "facebook", query["id"][0]
        return "facebook", path.split("/")[0]

    if "instagram.com" in domain:
        return "instagram", path.split("/")[0]

    if "twitter.com" in domain or "x.com" in domain:
        return "twitter", path.split("/")[0]

    return "website", domain


# -------------------------------
# Website checker
# -------------------------------
def check_website(url):
    try:
        if not url.startswith("http"):
            url = "https://" + url

        headers = {"User-Agent": "Mozilla/5.0"}

        r = requests.get(url, headers=headers, allow_redirects=True, timeout=8)
        final_url = r.url

        if final_url.rstrip("/") != url.rstrip("/"):
            return "NO", "Redirects to another website"

        if r.status_code == 200:
            return "YES", "Website exists"

        return "NO", f"HTTP {r.status_code}"

    except:
        return "NO", "Website not reachable"


# -------------------------------
# 🔥 Selenium checker (MAIN FIX)
# -------------------------------
def check_with_selenium(url):
    try:
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        # 👉 Railway path (fallback to local if not present)
        chrome_driver_path = os.environ.get("CHROMEDRIVER_PATH", None)

        if chrome_driver_path:
            service = Service(chrome_driver_path)
            driver = webdriver.Chrome(service=service, options=options)
        else:
            driver = webdriver.Chrome(options=options)

        driver.get(url)
        time.sleep(5)

        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        driver.quit()

        # ---------------- INSTAGRAM ----------------
        if "instagram.com" in url:
            if "sorry, this page isn't available" in page_text:
                return "NO", "Profile not available"
            if "page isn't available" in page_text:
                return "NO", "Profile removed"
            if "log in" in page_text and "sign up" in page_text:
                return "UNKNOWN", "Login required"

            return "YES", "Profile exists"

        # ---------------- X (TWITTER) ----------------
        if "x.com" in url or "twitter.com" in url:
            if "this account doesn’t exist" in page_text:
                return "NO", "Account does not exist"
            if "account suspended" in page_text:
                return "NO", "Account suspended"

            return "YES", "Profile exists"

        return "UNKNOWN", "Unknown platform"

    except Exception as e:
        return "NO", str(e)


# -------------------------------
# 🔥 Main user checker
# -------------------------------
def check_user(platform, username, url=None):

    username = str(username)
    platform = str(platform).lower()

    try:

        # ---------------- SOCIAL MEDIA ----------------
        if platform in ["instagram", "twitter", "x"]:

            quick_status = "NO"

            # ⚡ FAST CHECK (socialscan)
            try:
                temp_json = tempfile.NamedTemporaryFile(delete=False, suffix=".json")

                subprocess.run(
                    [
                        "python", "-m", "socialscan",
                        username,
                        "--platforms",
                        platform,
                        "--json",
                        temp_json.name
                    ],
                    capture_output=True,
                    text=True,
                    timeout=25
                )

                with open(temp_json.name) as f:
                    content = f.read().strip()

                    if content:
                        data = json.loads(content)

                        if username in data:
                            for result in data[username]:
                                if result["platform"].lower() == platform:
                                    if result["available"] == "False" and result["valid"]:
                                        quick_status = "YES"

            except:
                pass

            # ❌ Username not taken
            if quick_status == "NO":
                return "NO", "Username not found"

            # 🔥 FINAL CHECK WITH SELENIUM
            selenium_status, reason = check_with_selenium(url)

            return selenium_status, reason

        # ---------------- WEBSITE ----------------
        if platform == "website":
            return check_website(url)

        # ---------------- OTHER PLATFORMS ----------------
        result = subprocess.run(
            ["python", "-m", "maigret", username, "--site", platform],
            capture_output=True,
            text=True,
            timeout=40
        )

        output = result.stdout.lower()

        if "[+]" in output and platform in output:
            return "YES", "Profile exists"

        return "NO", "Profile not found"

    except Exception as e:
        print("Error:", e)
        return "NO", str(e)


# -------------------------------
# Routes
# -------------------------------
@app.route("/")
def home():
    return {"status": "API running"}


@app.route("/check_url", methods=["POST"])
def check_url():

    data = request.json
    url = data.get("url")

    if not url:
        return {"error": "No URL"}

    platform, username = extract_platform_username(url)

    if platform == "website":
        status, reason = check_website(url)
    else:
        status, reason = check_user(platform, username, url)

    return {
        "platform": platform.capitalize(),
        "status": status,
        "reason": reason
    }


@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        file = request.files["file"]
        df = pd.read_excel(file)

        if "urls" not in df.columns:
            return {"error": "Excel must contain 'urls' column"}

        df["status"] = ""
        df["platform"] = ""
        df["reason"] = ""

        for index, row in df.iterrows():
            url = str(row["urls"])

            platform, username = extract_platform_username(url)

            status, reason = check_user(platform, username, url)

            df.at[index, "platform"] = platform.capitalize()
            df.at[index, "status"] = status
            df.at[index, "reason"] = reason

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        df.to_excel(temp_file.name, index=False)

        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name="updated_status.xlsx"
        )

    except Exception as e:
        return {"error": str(e)}, 500


# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
