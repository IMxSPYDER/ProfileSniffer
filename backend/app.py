import os
from flask import Flask, request, send_file
from flask_cors import CORS
import pandas as pd
import subprocess
import tempfile
import json
import requests
from urllib.parse import urlparse

# Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
# from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

import time

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

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
# Selenium checker
# -------------------------------
def check_with_selenium(url):
    try:
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument("--window-size=1920,1080")

        options.binary_location = "/usr/bin/chromium"

        service = Service("/usr/lib/chromium/chromedriver")

        driver = webdriver.Chrome(service=service, options=options)
        
        driver.set_page_load_timeout(50)
        driver.get(url)
        time.sleep(5)

        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        driver.quit()

        print(page_text)

        NOT_FOUND = [
        "sorry, this page isn't available",
        "page not found",
        "content unavailable",
        "the link you followed may be broken",
        "profile isn't available",
        "profile may have been removed",
        "the page may have been removed",
        "this account doesn’t exist",
        "try searching for another"
        ]


        # -------- Instagram --------
        if "instagram.com" in url:
            if any(keyword in page_text for keyword in NOT_FOUND):
                return "NO", "Profile not available"
            return "YES", "Profile exists"

        # -------- Twitter / X --------
        if "x.com" in url or "twitter.com" in url:
            if any(keyword in page_text for keyword in NOT_FOUND):
                return "NO", "Profile not available"
            return "YES", "Profile exists"

        return "UNKNOWN", "Unknown platform"

    except Exception as e:
        print("Selenium error:", e)
        return "NO", str(e)

# -------------------------------
# Main checker
# -------------------------------
def check_user(platform, username, url=None):
    username = str(username)
    platform = str(platform).lower()

    try:
        # -------- SOCIAL MEDIA --------
        if platform in ["instagram", "twitter", "x"]:

            quick_status = "NO"

            # STEP 1: socialscan
            try:
                temp_json = tempfile.NamedTemporaryFile(delete=False, suffix=".json")

                subprocess.run(
                    [
                        "socialscan",
                        username,
                        "--platforms", platform,
                        "--json", temp_json.name
                    ],
                    capture_output=True,
                    text=True,
                    timeout=20
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

            except Exception as e:
                print("Socialscan error:", e)

            # STEP 2: stop if not found
            if quick_status == "NO":
                return "NO", "Username not found"

            # STEP 3: verify with Selenium
            selenium_status, reason = check_with_selenium(url)

            if selenium_status == "YES":
                return "YES", "Profile exists"
            elif selenium_status == "NO":
                return "NO", reason
            else:
                return "YES", "Username exists (partial verification)"

        # -------- WEBSITE --------
        if platform == "website":
            return check_website(url)

        # -------- OTHER (Maigret) --------
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
# Run locally
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
