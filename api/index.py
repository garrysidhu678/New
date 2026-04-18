from flask import Flask, request
import requests
import base64
import zipfile
import tempfile
import os

BOT_TOKEN = "YOUR_BOT_TOKEN"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)
user_sessions = {}

# ===== Send message =====
def send_msg(chat_id, text):
    requests.post(f"{TELEGRAM_API}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

# ===== Send photo =====
def send_photo(chat_id, url, caption=""):
    requests.post(f"{TELEGRAM_API}/sendPhoto", json={
        "chat_id": chat_id,
        "photo": url,
        "caption": caption
    })

# ===== Create repo =====
def create_repo(token, repo):
    headers = {"Authorization": f"token {token}"}
    name = repo.split("/")[-1]
    requests.post("https://api.github.com/user/repos",
                  headers=headers,
                  json={"name": name, "private": False})

# ===== Upload file =====
def upload_file(token, repo, path, content):
    headers = {"Authorization": f"token {token}"}
    url = f"https://api.github.com/repos/{repo}/contents/{path}"

    data = {
        "message": "upload from bot",
        "content": base64.b64encode(content).decode()
    }
    requests.put(url, headers=headers, json=data)

# ===== Handle updates =====
@app.route("/", methods=["POST"])
def webhook():
    data = request.json

    if "message" not in data:
        return "ok"

    msg = data["message"]
    chat_id = msg["chat"]["id"]

    # ===== /start =====
    if msg.get("text") == "/start":
        user_sessions[chat_id] = {"step": "token"}
        send_msg(chat_id, "Send GitHub token")
        return "ok"

    # ===== /help =====
    if msg.get("text") == "/help":
        send_photo(chat_id, "https://graph.org/file/36f8244a80aa0b6c8af9b-929ce809f9abf6c044.jpg", "Step 1")
        send_photo(chat_id, "https://graph.org/file/2dad9fdf0224078648f58-208ccc708cb4de0031.jpg", "Step 2")
        send_photo(chat_id, "https://graph.org/file/82ec6de6452f834830858-858cc8e14779ce36a9.jpg", "Step 3")
        send_photo(chat_id, "https://graph.org/file/90a782f47438f854c0da6-e02a6b739362ca9700.jpg", "Step 4")
        return "ok"

    # ===== Text steps =====
    if "text" in msg and chat_id in user_sessions:
        step = user_sessions[chat_id]["step"]

        if step == "token":
            user_sessions[chat_id]["token"] = msg["text"]
            user_sessions[chat_id]["step"] = "repo"
            send_msg(chat_id, "Send repo username/repo")
            return "ok"

        elif step == "repo":
            user_sessions[chat_id]["repo"] = msg["text"]
            user_sessions[chat_id]["step"] = "zip"
            send_msg(chat_id, "Send ZIP file")
            return "ok"

    # ===== Handle ZIP =====
    if "document" in msg and chat_id in user_sessions:
        file_id = msg["document"]["file_id"]

        file_info = requests.get(f"{TELEGRAM_API}/getFile?file_id={file_id}").json()
        file_path = file_info["result"]["file_path"]

        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        file_data = requests.get(file_url).content

        temp = tempfile.mkdtemp()
        zip_path = os.path.join(temp, "file.zip")

        with open(zip_path, "wb") as f:
            f.write(file_data)

        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp)

            token = user_sessions[chat_id]["token"]
            repo = user_sessions[chat_id]["repo"]

            create_repo(token, repo)

            # upload files
            for root, _, files in os.walk(temp):
                for file in files:
                    if file.endswith(".zip"):
                        continue
                    full = os.path.join(root, file)
                    rel = os.path.relpath(full, temp)

                    with open(full, "rb") as f:
                        upload_file(token, repo, rel, f.read())

            send_msg(chat_id, "✅ Uploaded to GitHub")

        except Exception as e:
            send_msg(chat_id, f"Error: {e}")

        return "ok"

    return "ok"
