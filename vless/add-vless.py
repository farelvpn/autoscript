#!/usr/bin/env python3
import sys
import json
import os
import re
import subprocess
import uuid
import threading

# --- Konfigurasi Path ---
PATH_CONFIG = '/etc/xray/config.json'
PATH_DOMAIN = '/etc/xray/domain'
PATH_BOT_KEY = '/etc/xray/bot.key'
PATH_CLIENT_ID = '/etc/xray/client.id'
DIR_DATABASE = '/etc/xray/database/vless'
DIR_QUOTA = '/etc/xray/limit/quota/vless'

# --- Fungsi Bantuan ---

def print_json_response(data, success=True, code=201):
    response = {"status": str(success).lower(), "code": code}
    if success:
        response["message"] = data.pop("message", "Akun VLESS berhasil dibuat")
        response["data"] = data
    else:
        response["message"] = data.get("message", "Terjadi kesalahan")
    print(json.dumps(response, indent=4))
    sys.exit(0 if success else 1)

def get_config_value(file_path, default="not-set"):
    try:
        with open(file_path, 'r') as f: return f.read().strip()
    except FileNotFoundError: return default

def validate_input(value, pattern):
    return re.match(pattern, str(value))

def check_user_exists(username):
    try:
        with open(PATH_CONFIG, 'r') as f: return f'"email": "{username}"' in f.read()
    except FileNotFoundError: return False

def add_user_to_config(username, user_uuid):
    try:
        with open(PATH_CONFIG, 'r') as f: lines = f.readlines()
        entry_to_add = [
            f'#@ {username}\n',
            f', {{"id": "{user_uuid}","email": "{username}"}}\n'
        ]
        for i, line in enumerate(lines):
            if '// #vless$' in line:
                lines[i] = "".join(entry_to_add) + line
                break
        else: return False
        with open(PATH_CONFIG, 'w') as f: f.writelines(lines)
        return True
    except (IOError, FileNotFoundError): return False

def send_telegram_notification(data):
    bot_token = get_config_value(PATH_BOT_KEY)
    chat_id = get_config_value(PATH_CLIENT_ID)
    if bot_token == "not-set" or chat_id == "not-set": return

    text = (
        f"<b>✅ VLESS ACCOUNT CREATED</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>👤 Username : </b> <code>{data['username']}</code>\n"
        f"<b>🔑 UUID     : </b> <code>{data['uuid']}</code>\n"
        f"<b>🌐 Hostname : </b> <code>{data['domain']}</code>\n"
        f"<b>📊 Quota    : </b> <code>{data['limits']['quota_display']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>Link (TLS):</b>\n<code>{data['links']['vless_ws_tls']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>Link (Non-TLS):</b>\n<code>{data['links']['vless_ws_http']}</code>"
    )
    
    def send_request():
        try:
            subprocess.run(
                ["curl", "-s", "-X", "POST", f"https://api.telegram.org/bot{bot_token}/sendMessage",
                 "-d", f"chat_id={chat_id}", "-d", "parse_mode=HTML", "-d", f"text={text}"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10
            )
        except Exception: pass
    threading.Thread(target=send_request).start()

# --- Logika Utama ---
def create_vless_account(params):
    username = params.get("username")
    quota_gb = params.get("quota")
    user_uuid = params.get("uuid") or str(uuid.uuid4())
    
    if not all([username, quota_gb is not None]):
        print_json_response({"message": "'username' dan 'quota' wajib diisi."}, success=False, code=400)
    if not validate_input(username, r"^[a-zA-Z0-9_]+$"): print_json_response({"message": "Username format salah."}, success=False, code=400)
    if not validate_input(quota_gb, r"^\d+$"): print_json_response({"message": "Quota harus angka."}, success=False, code=400)
    if check_user_exists(username): print_json_response({"message": "Username ini sudah ada."}, success=False, code=409)

    for d in [DIR_DATABASE, DIR_QUOTA]: os.makedirs(d, exist_ok=True)

    quota_bytes = quota_gb * (1024**3) if quota_gb > 0 else 0
    with open(os.path.join(DIR_QUOTA, username), 'w') as f: f.write(str(quota_bytes))

    if not add_user_to_config(username, user_uuid):
        print_json_response({"message": "Gagal update config. Pastikan marker '// #vless$' ada."}, success=False, code=500)

    db_content = f"username: {username}\nuuid: {user_uuid}\nquota: {quota_gb}\n"
    with open(os.path.join(DIR_DATABASE, f"{username}.txt"), 'w') as f: f.write(db_content)

    domain = get_config_value(PATH_DOMAIN, "domain-not-set")
    link_tls = f"vless://{user_uuid}@{domain}:443?path=/vless&security=tls&encryption=none&type=ws&host={domain}&sni={domain}#{username}"
    link_http = f"vless://{user_uuid}@{domain}:80?path=/vless&encryption=none&type=ws&host={domain}#{username}"

    try: subprocess.run(["systemctl", "restart", "xray.service"], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e: print_json_response({"message": f"Gagal restart Xray: {e.stderr}"}, success=False, code=500)

    response_data = {
        "username": username, "uuid": user_uuid, "domain": domain,
        "limits": {
            "quota": quota_gb, "quota_display": "Unlimited" if quota_gb == 0 else f"{quota_gb} GB", "quota_bytes": quota_bytes
        },
        "ports": {"vless_ws_tls": 443, "vless_ws_http": 80},
        "links": {"vless_ws_tls": link_tls, "vless_ws_http": link_http}
    }
    
    send_telegram_notification(response_data)
    print_json_response(response_data)

if __name__ == "__main__":
    try:
        params = json.loads(sys.stdin.read())
        if 'quota' in params: params['quota'] = int(params['quota'])
        create_vless_account(params)
    except (json.JSONDecodeError, ValueError):
        print_json_response({"message": "Input JSON tidak valid."}, success=False, code=400)
    except Exception as e:
        print_json_response({"message": f"Error: {str(e)}"}, success=False, code=500)
