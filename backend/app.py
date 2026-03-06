from flask import Flask, request, send_file
from flask_cors import CORS
import pandas as pd
import subprocess
import tempfile
import json

app = Flask(__name__)

CORS(app)

def check_user(platform, username):

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
                data = json.load(f)

            if username in data:

                for result in data[username]:

                    if result["platform"].lower() == platform:

                        if result["available"] == "False" and result["valid"] == "True":
                            return "YES"
                        else:
                            return "NO"

            return "NO"

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

@app.route("/upload", methods=["POST"])
def upload_file():

    file = request.files["file"]
    df = pd.read_excel(file)

    # Ensure status column exists
    if "status" not in df.columns:
        df["status"] = ""
    else:
        df["status"] = df["status"].astype(str)

    for index, row in df.iterrows():
        platform = str(row["platform"])
        username = str(row["username"])

        status = check_user(platform, username)
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
    # app.run(debug=True)
    app.run()