# from flask import Flask, request, send_file
# from flask_cors import CORS
# import pandas as pd
# import subprocess
# import tempfile
# import json

# app = Flask(__name__)

# CORS(app)

# def check_user(platform, username):

#     username = str(username)
#     platform = str(platform).lower()

#     try:

#         if platform in ["instagram", "twitter", "x"]:

#             temp_json = tempfile.NamedTemporaryFile(delete=False, suffix=".json")

#             subprocess.run(
#                 [
#                     "socialscan",
#                     username,
#                     "--platforms",
#                     platform,
#                     "--json",
#                     temp_json.name
#                 ],
#                 capture_output=True,
#                 text=True
#             )

#             with open(temp_json.name) as f:
#                 content = f.read().strip()

#                 if not content:
#                     return "NO"

#                 data = json.loads(content)

#             if username in data:

#                 for result in data[username]:

#                     if result["platform"].lower() == platform:

#                         if result["available"] == "False" and result["valid"]:
#                             return "YES"
#                         else:
#                             return "NO"

#             return "NO"

#         else:

#             result = subprocess.run(
#                 ["maigret", username, "--site", platform],
#                 capture_output=True,
#                 text=True
#             )

#             output = result.stdout.lower()

#             if "[+]" in output and platform in output:
#                 return "YES"

#             return "NO"

#     except Exception as e:
#         print("Error:", e)
#         return "NO"

# @app.route("/upload", methods=["POST"])
# def upload_file():

#     file = request.files["file"]
#     df = pd.read_excel(file)

#     # Ensure status column exists
#     if "status" not in df.columns:
#         df["status"] = ""
#     else:
#         df["status"] = df["status"].astype(str)

#     for index, row in df.iterrows():
#         platform = str(row["platform"])
#         username = str(row["username"])

#         status = check_user(platform, username)
#         df.at[index, "status"] = status

#     temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")

#     df.to_excel(temp_file.name, index=False)

#     return send_file(
#         temp_file.name,
#         as_attachment=True,
#         download_name="updated_status.xlsx",
#         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#     )


# if __name__ == "__main__":
#     app.run(debug=True)
#     # app.run()
import os
from flask import Flask, request, send_file
from flask_cors import CORS
import pandas as pd
import subprocess
import tempfile
import json
import requests
from urllib.parse import urlparse

app = Flask(__name__)

CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=True
)


def extract_platform_username(url):

    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path.strip("/")

    # Facebook profile id
    if "facebook.com" in domain:

        if "profile.php" in url:
            import urllib.parse
            query = urllib.parse.parse_qs(parsed.query)

            if "id" in query:
                return "facebook", query["id"][0]

        return "facebook", path.split("/")[0]

    # Instagram
    if "instagram.com" in domain:
        return "instagram", path.split("/")[0]

    # Twitter / X
    if "twitter.com" in domain or "x.com" in domain:
        return "twitter", path.split("/")[0]

    # website
    return "website", domain

def check_website(url):
    try:
        r = requests.head(url, allow_redirects=True, timeout=5)

        if r.status_code < 400:
            return "YES"
        else:
            return "NO"

    except Exception:
        return "NO"

def check_user(platform, username, url=None):

    username = str(username)
    platform = str(platform).lower()

    try:

        if platform in ["instagram", "twitter", "x"]:

            temp_json = tempfile.NamedTemporaryFile(delete=False, suffix=".json")

            subprocess.run(
                [
                    "socialscan",
                    username,
                    "--platforms",
                    platform,
                    "--json",
                    temp_json.name
                ],
                capture_output=True,
                text=True
            )

            with open(temp_json.name) as f:
                content = f.read().strip()

                if not content:
                    return "NO"

                data = json.loads(content)

            if username in data:

                for result in data[username]:

                    if result["platform"].lower() == platform:
                        if result["available"] == "False" and result["valid"]:
                            return "YES"

            return "NO"
        
        # NORMAL WEBSITE
        if platform == "website":
            return check_website(url)

        else:

            result = subprocess.run(
                ["maigret", username, "--site", platform],
                capture_output=True,
                text=True
            )

            output = result.stdout.lower()

            if "[+]" in output and platform in output:
                return "YES"

            return "NO"

    except Exception as e:
        print("Error:", e)
        return "NO"

@app.route("/")
def home():
    return {"status": "API running"}

@app.route("/upload", methods=["POST", "OPTIONS"])
def upload_file():

    file = request.files["file"]

    df = pd.read_excel(file)

    # Expect only urls column
    if "urls" not in df.columns:
        return {"error": "Excel must contain 'urls' column"}
    
    if "status" not in df.columns:
        df["status"] = ""

    if "platform" not in df.columns:
        df["platform"] = ""

    
    df["platform"] = df["platform"].astype(str)
    df["status"] = df["status"].astype(str)

    
    for index, row in df.iterrows():

        url = str(row["urls"])

        platform, username = extract_platform_username(url)

        df.at[index, "platform"] = platform.capitalize()

        status = check_user(platform, username, url)

        df.at[index, "status"] = status

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")

    df.to_excel(temp_file.name, index=False)

    return send_file(
        temp_file.name,
        as_attachment=True,
        download_name="updated_status.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
    
