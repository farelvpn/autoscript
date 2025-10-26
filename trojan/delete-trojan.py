#!/usr/bin/env python3
import sys
import json
import os
import re
import subprocess
import threading

# --- Konfigurasi Path & Konstanta ---
PATH_CONFIG = '/etc/xray/config.json'
PATH_DOMAIN = '/etc/xray/domain'
PATH_BOT_KEY = '/etc/xray/bot.key'
PATH_CLIENT_ID = '/etc/xray/client.id'
DIR_QUOTA = '/etc/xray/limit/quota/trojan'
DIR_DATABASE = '/etc/xray/database/trojan'

# --- Fungsi Bantuan (Helpers) ---

def print_json_response(data, success=True, code=200):
    """Mencetak output dalam format JSON standar."""
    response = {
        "status": str(success).lower(),
        "code": code,
    }
    if success:
        response["message"] = data.pop("message", f"Akun '{data.get('username')}' berhasil dihapus permanen")
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

def parse_db_file(file_path):
    """Membaca file database user dan mengembalikannya sebagai dictionary."""
    user_info = {}
    try:
        with open(file_path, 'r') as f:
            for line in f:
                if ":" in line:
                    key, value = line.split(":", 1)
                    user_info[key.strip()] = value.strip()
    except FileNotFoundError:
        return None
    return user_info

def remove_user_from_config(username):
    """Menghapus user dari file config.json dengan aman."""
    try:
        with open(PATH_CONFIG, 'r') as f:
            lines = f.readlines()

        new_lines = []
        skip_next_line = False
        user_found = False

        for line in lines:
            if skip_next_line:
                skip_next_line = False
                continue
            
            if line.strip() == f'#@ {username}':
                skip_next_line = True
                user_found = True
                continue
            
            new_lines.append(line)
        
        if not user_found:
            return True

        full_config = "".join(new_lines)
        full_config = re.sub(r',\s*\n(\s*})', r'\n\1', full_config)

        with open(PATH_CONFIG, 'w') as f:
            f.write(full_config)
            
        return True
    except (IOError, FileNotFoundError):
        return False

def send_telegram_notification(username):
    """Mengirim notifikasi penghapusan ke Telegram."""
    bot_token = get_config_value(PATH_BOT_KEY)
    chat_id = get_config_value(PATH_CLIENT_ID)

    if bot_token == "not-set" or chat_id == "not-set":
        return

    text = (
        f"<b>ACCOUNT DELETED (PERMANENT)</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<b>Username : </b> <code>{username}</code>\n"
        f"<b>Status   : </b> DELETED"
    )

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

def delete_trojan_account(params):
    """Fungsi utama untuk menghapus akun Trojan secara permanen."""
    username = params.get("username")

    # 1. Validasi Input
    if not username:
        print_json_response({"message": "Input JSON tidak valid. 'username' wajib diisi."}, success=False, code=400)

    db_path = os.path.join(DIR_DATABASE, f"{username}.txt")
    if not os.path.exists(db_path):
        print_json_response({"message": f"User '{username}' tidak ditemukan."}, success=False, code=404)

    # 2. Baca Info User (untuk respons)
    user_info = parse_db_file(db_path)
    user_uuid = user_info.get("uuid", "N/A")

    # 3. Hapus File Database Secara Permanen
    try:
        os.remove(db_path)
    except OSError as e:
        print_json_response({"message": f"Gagal menghapus file database: {e}"}, success=False, code=500)

    # 4. Hapus File-file Terkait Lainnya
    files_removed = ["database"]
    quota_path = os.path.join(DIR_QUOTA, username)
    if os.path.exists(quota_path):
        os.remove(quota_path)
        files_removed.append("quota_limit")
    
    # 5. Hapus User dari Konfigurasi
    if not remove_user_from_config(username):
        print_json_response({"message": "Gagal memperbarui file konfigurasi Xray."}, success=False, code=500)
    
    # 6. Restart Layanan Xray
    try:
        subprocess.run(["systemctl", "restart", "xray.service", "quota-trojan.service"], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print_json_response({"message": f"Gagal me-restart layanan Xray: {e.stderr}"}, success=False, code=500)
        
    # 7. Kirim Notifikasi & Respons
    send_telegram_notification(username)

    response_data = {
        "username": username,
        "uuid": user_uuid,
        "files_removed": files_removed
    }
    
    print_json_response(response_data, success=True, code=200)

if __name__ == "__main__":
    try:
        input_json = sys.stdin.read()
        params = json.loads(input_json)
        delete_trojan_account(params)
    except json.JSONDecodeError:
        print_json_response({"message": "Gagal mem-parsing input. Pastikan format JSON sudah benar."}, success=False, code=400)
    except Exception as e:
        print_json_response({"message": f"Terjadi kesalahan internal: {str(e)}"}, success=False, code=500)
