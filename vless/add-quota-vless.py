#!/usr/bin/env python3
import os
import sys
import json
import subprocess

# --- Konfigurasi Path ---
DIR_QUOTA_LIMIT = '/etc/xray/limit/quota/vless'
DIR_DATABASE = '/etc/xray/database/vless'
PATH_BOT_KEY = '/etc/xray/bot.key'
PATH_CLIENT_ID = '/etc/xray/client.id'

# --- Fungsi Bantuan ---

def print_json_response(data, success=True, code=200):
    """Mencetak output dalam format JSON standar."""
    response = {
        "status": str(success).lower(),
        "code": code,
    }
    if success:
        response["message"] = f"Kuota untuk user VLESS '{data.get('username')}' berhasil ditambahkan"
        response["data"] = data
    else:
        response["message"] = data.get("message", "Terjadi kesalahan")
    
    print(json.dumps(response, indent=4))
    sys.exit(0 if success else 1)

def bytes_to_human(byte_count):
    """Mengonversi byte menjadi format GB yang mudah dibaca."""
    if byte_count is None or byte_count == 0:
        return "0 GB"
    gb_value = byte_count / (1024**3)
    return f"{gb_value:.2f} GB"

def send_telegram_notification(username, quota_added_gb, new_total_quota_display):
    """Mengirim notifikasi penambahan kuota ke Telegram."""
    try:
        if not os.path.exists(PATH_BOT_KEY) or not os.path.exists(PATH_CLIENT_ID):
            return

        with open(PATH_BOT_KEY, 'r') as f:
            bot_token = f.read().strip()
        with open(PATH_CLIENT_ID, 'r') as f:
            chat_id = f.read().strip()

        if not bot_token or not chat_id:
            return

        message = (
            f"<b>✅ VLESS KUOTA DITAMBAHKAN</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<b>👤 Username : </b> <code>{username}</code>\n"
            f"<b>➕ Ditambah : </b> <code>{quota_added_gb} GB</code>\n"
            f"<b>📊 Total Baru: </b> <code>{new_total_quota_display}</code>"
        )

        subprocess.run(
            ["curl", "-s", "-X", "POST", f"https://api.telegram.org/bot{bot_token}/sendMessage",
             "-d", f"chat_id={chat_id}", "-d", "parse_mode=HTML", "-d", f"text={message}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10
        )
    except Exception as e:
        print(f"WARNING: Gagal mengirim notifikasi Telegram: {e}", file=sys.stderr)

# --- Logika Utama ---

def add_vless_user_quota(params):
    """Fungsi utama untuk menambahkan kuota ke user VLESS."""
    username = params.get("username")
    additional_quota_gb = params.get("add_quota")

    # 1. Validasi Input
    if not all([username, additional_quota_gb is not None]):
        print_json_response({"message": "Input JSON tidak valid. 'username' dan 'add_quota' wajib diisi."}, success=False, code=400)
    
    try:
        additional_quota_gb = int(additional_quota_gb)
        if additional_quota_gb <= 0:
            raise ValueError("Kuota harus lebih dari 0")
    except (ValueError, TypeError):
        print_json_response({"message": "'add_quota' harus berupa angka positif (integer)."}, success=False, code=400)

    # 2. Cek apakah user ada
    db_path = os.path.join(DIR_DATABASE, f"{username}.txt")
    if not os.path.exists(db_path):
        print_json_response({"message": f"User VLESS '{username}' tidak ditemukan."}, success=False, code=404)

    # 3. Kalkulasi Kuota Baru
    limit_file = os.path.join(DIR_QUOTA_LIMIT, username)
    current_limit_bytes = 0
    try:
        if os.path.exists(limit_file):
            with open(limit_file, 'r') as f:
                content = f.read().strip()
                if content:
                    current_limit_bytes = int(content)
    except (IOError, ValueError) as e:
        print_json_response({"message": f"Gagal membaca file kuota saat ini: {e}"}, success=False, code=500)

    additional_bytes = additional_quota_gb * (1024**3)
    new_total_bytes = current_limit_bytes + additional_bytes

    # 4. Tulis Kuota Baru ke File
    try:
        with open(limit_file, 'w') as f:
            f.write(str(new_total_bytes))
    except IOError as e:
        print_json_response({"message": f"Gagal menulis file kuota baru: {e}"}, success=False, code=500)

    # 5. Kirim Notifikasi Telegram
    new_total_quota_display = bytes_to_human(new_total_bytes)
    send_telegram_notification(username, additional_quota_gb, new_total_quota_display)

    # 6. Susun Respons JSON
    response_data = {
        "username": username,
        "quota_added": {
            "gb": additional_quota_gb,
            "bytes": additional_bytes
        },
        "previous_total_quota": {
            "gb_display": bytes_to_human(current_limit_bytes),
            "bytes": current_limit_bytes
        },
        "new_total_quota": {
            "gb_display": new_total_quota_display,
            "bytes": new_total_bytes
        },
        "telegram_notification": "sent"
    }
    
    print_json_response(response_data)


if __name__ == "__main__":
    try:
        input_json = sys.stdin.read()
        params = json.loads(input_json)
        add_vless_user_quota(params)
    except json.JSONDecodeError:
        print_json_response({"message": "Gagal mem-parsing input. Pastikan format JSON sudah benar."}, success=False, code=400)
    except Exception as e:
        print_json_response({"message": f"Terjadi kesalahan internal: {str(e)}"}, success=False, code=500)
