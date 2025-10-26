#!/usr/bin/env python3
import sys
import json
import os
import re
import subprocess
import uuid
import base64
import threading

# --- Konfigurasi Path ---
PATH_CONFIG = '/etc/xray/config.json'
PATH_DOMAIN = '/etc/xray/domain'
PATH_BOT_KEY = '/etc/xray/bot.key'
PATH_CLIENT_ID = '/etc/xray/client.id'
DIR_DATABASE_VMESS = '/etc/xray/database/vmess'
DIR_QUOTA_VMESS = '/etc/xray/limit/quota/vmess'

# --- Fungsi Bantuan ---

def print_json_response(data, success=True, code=201):
    """Mencetak output dalam format JSON standar."""
    response = {"status": str(success).lower(), "code": code}
    if success:
        response["message"] = data.pop("message", "Akun VMESS berhasil dibuat")
        response["data"] = data
    else:
        response["message"] = data.get("message", "Terjadi kesalahan")
    print(json.dumps(response, indent=4))
    sys.exit(0 if success else 1)

def get_config_value(file_path, default="not-set"):
    """Membaca nilai dari file konfigurasi dengan aman."""
    try:
        with open(file_path, 'r') as f: return f.read().strip()
    except FileNotFoundError: return default

def validate_input(value, pattern):
    """Memvalidasi input menggunakan regular expression."""
    return re.match(pattern, str(value))

def check_user_exists(username):
    """Mengecek apakah username sudah ada di config.json."""
    try:
        with open(PATH_CONFIG, 'r') as f: return f'"email": "{username}"' in f.read()
    except FileNotFoundError: return False

def add_user_to_config(username, user_uuid):
    """Menyisipkan data user baru ke dalam file config.json."""
    try:
        with open(PATH_CONFIG, 'r') as f: lines = f.readlines()
        
        entry_to_add = [
            f'#@ {username}\n',
            f', {{"id": "{user_uuid}","alterId": 0,"email": "{username}"}}\n'
        ]
        
        for i, line in enumerate(lines):
            if '// #vmess$' in line:
                lines[i] = "".join(entry_to_add) + line
                break
        else:
            return False

        with open(PATH_CONFIG, 'w') as f: f.writelines(lines)
        return True
    except (IOError, FileNotFoundError): return False

def send_telegram_notification(data):
    """Mengirim notifikasi ke Telegram di thread terpisah."""
    bot_token = get_config_value(PATH_BOT_KEY)
    chat_id = get_config_value(PATH_CLIENT_ID)
    if bot_token == "not-set" or chat_id == "not-set": return

    text = (
        f"<b>✅ VMESS ACCOUNT CREATED</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>👤 Username : </b> <code>{data['username']}</code>\n"
        f"<b>🔑 UUID     : </b> <code>{data['uuid']}</code>\n"
        f"<b>🌐 Hostname : </b> <code>{data['domain']}</code>\n"
        f"<b>📊 Quota    : </b> <code>{data['limits']['quota_display']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>Ports & Service</b>\n"
        f"<b>- VMESS WS TLS : </b> <code>{data['ports']['vmess_ws_tls']}</code>\n"
        f"<b>- VMESS WS HTTP: </b> <code>{data['ports']['vmess_ws_http']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>Link (TLS):</b>\n<code>{data['links']['vmess_ws_tls']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>Link (Non-TLS):</b>\n<code>{data['links']['vmess_ws_http']}</code>"
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

def create_vmess_account(params):
    """Fungsi utama untuk membuat akun VMESS."""
    username = params.get("username")
    quota_gb = params.get("quota")
    user_uuid = params.get("uuid") or str(uuid.uuid4())
    
    # 1. Validasi Input
    if not all([username, quota_gb is not None]):
        print_json_response({"message": "Input JSON tidak valid. 'username' dan 'quota' wajib diisi."}, success=False, code=400)
    
    if not validate_input(username, r"^[a-zA-Z0-9_]+$"): print_json_response({"message": "Username format salah."}, success=False, code=400)
    if not validate_input(quota_gb, r"^\d+$"): print_json_response({"message": "Quota harus angka."}, success=False, code=400)
    
    # 2. Cek Duplikasi
    if check_user_exists(username): print_json_response({"message": "Username ini sudah ada."}, success=False, code=409)

    # 3. Persiapan Direktori
    for d in [DIR_DATABASE_VMESS, DIR_QUOTA_VMESS]: os.makedirs(d, exist_ok=True)

    # 4. Pengaturan Kuota
    quota_bytes = quota_gb * (1024**3) if quota_gb > 0 else 0
    with open(os.path.join(DIR_QUOTA_VMESS, username), 'w') as f: f.write(str(quota_bytes))

    # 5. Menambahkan User ke Konfigurasi
    if not add_user_to_config(username, user_uuid):
        print_json_response({"message": "Gagal memperbarui file konfigurasi Xray. Pastikan marker '// #vmess$' ada."}, success=False, code=500)

    # 6. Menyimpan Database Akun
    db_content = f"username: {username}\nuuid: {user_uuid}\nquota: {quota_gb}\n"
    with open(os.path.join(DIR_DATABASE_VMESS, f"{username}.txt"), 'w') as f: f.write(db_content)

    # 7. Generate Link VMESS (TLS dan Non-TLS)
    domain = get_config_value(PATH_DOMAIN, "domain-not-set")
    vmess_tls_config = {"v": "2", "ps": username, "add": domain, "port": "443", "id": user_uuid, "aid": "0", "net": "ws", "path": "/vmess", "type": "none", "host": domain, "tls": "tls"}
    vmess_http_config = {"v": "2", "ps": username, "add": domain, "port": "80", "id": user_uuid, "aid": "0", "net": "ws", "path": "/vmess", "type": "none", "host": domain, "tls": "none"}
    
    link_tls = "vmess://" + base64.b64encode(json.dumps(vmess_tls_config).encode()).decode()
    link_http = "vmess://" + base64.b64encode(json.dumps(vmess_http_config).encode()).decode()

    # 8. Restart Layanan Xray
    try: subprocess.run(["systemctl", "restart", "xray.service"], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e: print_json_response({"message": f"Gagal me-restart layanan Xray: {e.stderr}"}, success=False, code=500)

    # 9. Membuat Respons JSON
    response_data = {
        "username": username, "uuid": user_uuid, "domain": domain,
        "limits": {
            "quota": quota_gb, "quota_display": "Unlimited" if quota_gb == 0 else f"{quota_gb} GB", "quota_bytes": quota_bytes
        },
        "ports": {
            "vmess_ws_tls": 443,
            "vmess_ws_http": 80
        },
        "links": {
            "vmess_ws_tls": link_tls,
            "vmess_ws_http": link_http
        }
    }
    
    send_telegram_notification(response_data)
    print_json_response(response_data)

if __name__ == "__main__":
    try:
        input_json = sys.stdin.read()
        params = json.loads(input_json)
        if 'quota' in params: params['quota'] = int(params['quota'])
        create_vmess_account(params)
    except (json.JSONDecodeError, ValueError):
        print_json_response({"message": "Input JSON tidak valid atau tipe data salah."}, success=False, code=400)
    except Exception as e:
        print_json_response({"message": f"Terjadi kesalahan internal: {str(e)}"}, success=False, code=500)
