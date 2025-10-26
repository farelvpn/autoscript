#!/usr/bin/env python3
# ========================================================
# Script Name: add-trojan (Python Version - No Expiry)
# Description: API script to create a non-expiring Trojan account for Xray.
# Executed by: Python WebAPI Server
# ========================================================

import sys
import json
import os
import re
import subprocess
import uuid
import threading

# --- Konfigurasi Path & Konstanta ---
PATH_CONFIG = '/etc/xray/config.json'
PATH_DOMAIN = '/etc/xray/domain'
PATH_BOT_KEY = '/etc/xray/bot.key'
PATH_CLIENT_ID = '/etc/xray/client.id'
DIR_QUOTA = '/etc/xray/limit/quota/trojan'
DIR_DATABASE = '/etc/xray/database/trojan'

# --- Fungsi Bantuan (Helpers) ---

def print_json_response(data, success=True, code=201):
    """Mencetak output dalam format JSON standar."""
    response = {
        "status": str(success).lower(),
        "code": code,
    }
    if success:
        response["message"] = data.pop("message", "Akun Trojan berhasil dibuat")
        response["data"] = data
    else:
        response["message"] = data.get("message", "Terjadi kesalahan")
    
    print(json.dumps(response, indent=4))
    sys.exit(0 if success else 1)

def get_config_value(file_path, default="not-set"):
    """Membaca nilai dari file konfigurasi dengan aman."""
    try:
        with open(file_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return default

def validate_input(value, pattern):
    """Memvalidasi input menggunakan regular expression."""
    return re.match(pattern, value)

def check_user_exists(username):
    """Mengecek apakah username sudah ada di config.json."""
    try:
        with open(PATH_CONFIG, 'r') as f:
            return f'"email": "{username}"' in f.read()
    except FileNotFoundError:
        return False

def add_user_to_config(username, user_uuid):
    """Menyisipkan data user baru ke dalam file config.json."""
    try:
        with open(PATH_CONFIG, 'r') as f:
            lines = f.readlines()

        new_lines = []
        user_added = False
        entry_to_add = [
            f'#@ {username}\n',
            f', {{"password": "{user_uuid}","email": "{username}"}}\n'
        ]

        for line in lines:
            new_lines.append(line)
            if '#trojan$' in line and not user_added:
                new_lines.extend(entry_to_add)
                user_added = True
        
        if not user_added:
            return False

        with open(PATH_CONFIG, 'w') as f:
            f.writelines(new_lines)
        
        return True
    except (IOError, FileNotFoundError):
        return False

def send_telegram_notification(data):
    """Mengirim notifikasi ke Telegram di thread terpisah."""
    bot_token = get_config_value(PATH_BOT_KEY)
    chat_id = get_config_value(PATH_CLIENT_ID)

    if bot_token == "not-set" or chat_id == "not-set":
        return

    text = (
        f"<b>TROJAN ACCOUNT CREATED</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>Username : </b> <code>{data['username']}</code>\n"
        f"<b>Password : </b> <code>{data['uuid']}</code>\n"
        f"<b>Hostname : </b> <code>{data['domain']}</code>\n"
        f"<b>Quota    : </b> <code>{data['limits']['quota_display']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>Link:</b>\n<code>{data['links']['trojan_ws_tls']}</code>"
    )
    
    # Menjalankan di thread agar tidak memblokir respons API
    def send_request():
        try:
            subprocess.run(
                ["curl", "-s", "-X", "POST", f"https://api.telegram.org/bot{bot_token}/sendMessage",
                 "-d", f"chat_id={chat_id}", "-d", "parse_mode=HTML", "-d", f"text={text}"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10
            )
        except Exception:
            pass 

    threading.Thread(target=send_request).start()

# --- Logika Utama ---

def create_trojan_account(params):
    """Fungsi utama untuk membuat akun Trojan."""
    username = params.get("username")
    quota_gb = params.get("quota")
    user_uuid = params.get("uuid") or str(uuid.uuid4())
    
    # 1. Validasi Input
    if not all([username, quota_gb is not None]):
        print_json_response({"message": "Input JSON tidak valid. 'username' dan 'quota' wajib diisi."}, success=False, code=400)
    
    if not validate_input(username, r"^[a-zA-Z0-9_]+$"):
        print_json_response({"message": "Username hanya boleh berisi huruf, angka, dan underscore."}, success=False, code=400)
    
    if not validate_input(str(quota_gb), r"^\d+$"):
        print_json_response({"message": "Quota harus berupa angka positif."}, success=False, code=400)

    # 2. Cek Duplikasi
    if check_user_exists(username):
        print_json_response({"message": "Username ini sudah ada."}, success=False, code=409)

    # 3. Persiapan Direktori
    os.makedirs(DIR_QUOTA, exist_ok=True)
    os.makedirs(DIR_DATABASE, exist_ok=True)

    # 4. Pengaturan Quota
    quota_bytes = 0
    quota_display = "Unlimited"
    if quota_gb > 0:
        quota_bytes = quota_gb * 1024 * 1024 * 1024
        quota_display = f"{quota_gb} GB"
        with open(os.path.join(DIR_QUOTA, username), 'w') as f:
            f.write(str(quota_bytes))

    # 5. Menambahkan User ke Konfigurasi
    if not add_user_to_config(username, user_uuid):
        print_json_response({"message": "Gagal memperbarui file konfigurasi Xray."}, success=False, code=500)

    # 6. Menyimpan Database Akun
    db_content = f"username: {username}\nuuid: {user_uuid}\nquota: {quota_gb}\n"
    with open(os.path.join(DIR_DATABASE, f"{username}.txt"), 'w') as f:
        f.write(db_content)

    # 7. Restart Layanan Xray
    try:
        subprocess.run(["systemctl", "restart", "xray.service"], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print_json_response({"message": f"Gagal me-restart layanan Xray: {e.stderr}"}, success=False, code=500)

    # 8. Membuat Respons JSON
    domain = get_config_value(PATH_DOMAIN, "domain-not-set")
    trojan_link = f"trojan://{user_uuid}@{domain}:443?type=ws&security=tls&host={domain}&path=/trojan&sni={domain}#{username}"
    
    response_data = {
        "username": username,
        "uuid": user_uuid,
        "domain": domain,
        "limits": {
            "quota_gb": quota_gb,
            "quota_display": quota_display,
            "quota_bytes": quota_bytes,
        },
        "ports": {
            "trojan_ws_tls": 443,
            "trojan_ws_http": 80,
        },
        "links": {
            "trojan_ws_tls": trojan_link,
        }
    }
    
    # 9. Kirim Notifikasi Telegram & Kirim Respons
    send_telegram_notification(response_data)
    print_json_response(response_data, success=True, code=201)

if __name__ == "__main__":
    try:
        input_json = sys.stdin.read()
        params = json.loads(input_json)
        create_trojan_account(params)
    except json.JSONDecodeError:
        print_json_response({"message": "Gagal mem-parsing input. Pastikan format JSON sudah benar."}, success=False, code=400)
    except Exception as e:
        print_json_response({"message": f"Terjadi kesalahan internal: {str(e)}"}, success=False, code=500)
