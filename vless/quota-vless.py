#!/usr/bin/env python3
import os
import sys
import subprocess
import re
import json

# --- Konfigurasi Path ---
PATH_CONFIG = '/etc/xray/config.json'
DIR_QUOTA_LIMIT = '/etc/xray/limit/quota/vless'
DIR_QUOTA_USAGE = '/etc/xray/usage/quota/vless'
DIR_DATABASE = '/etc/xray/database/vless'
PATH_BOT_KEY = '/etc/xray/bot.key'
PATH_CLIENT_ID = '/etc/xray/client.id'

# --- Fungsi-fungsi ---

def send_telegram_notification(username):
    """Mengirim notifikasi ke Telegram bahwa user telah dihapus."""
    try:
        if not os.path.exists(PATH_BOT_KEY) or not os.path.exists(PATH_CLIENT_ID):
            return

        with open(PATH_BOT_KEY, 'r') as f: bot_token = f.read().strip()
        with open(PATH_CLIENT_ID, 'r') as f: chat_id = f.read().strip()

        if not bot_token or not chat_id: return

        message = (
            f"<b>VLESS AKUN DIHAPUS (QUOTA HABIS)</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<b>Username : </b> <code>{username}</code>\n"
            f"<b>Alasan   : </b> Kuota data telah terlampaui."
        )

        subprocess.run(
            ["curl", "-s", "-X", "POST", f"https://api.telegram.org/bot{bot_token}/sendMessage",
             "-d", f"chat_id={chat_id}", "-d", "parse_mode=HTML", "-d", f"text={message}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10
        )
        print(f"INFO: Notifikasi penghapusan untuk '{username}' telah dikirim ke Telegram.")
    except Exception as e:
        print(f"ERROR: Gagal mengirim notifikasi Telegram: {e}", file=sys.stderr)

def get_all_users():
    """Mendapatkan daftar semua user dari file konfigurasi Xray."""
    try:
        with open(PATH_CONFIG, 'r') as f:
            content = f.read()
        users = re.findall(r'^#@\s+([^\s]+)', content, re.MULTILINE)
        return sorted(list(set(users)))
    except FileNotFoundError:
        print(f"ERROR: File konfigurasi tidak ditemukan di {PATH_CONFIG}", file=sys.stderr)
        return []

def delete_user_permanently(username):
    """Menghapus pengguna secara permanen dan mengirim notifikasi."""
    print(f"INFO: Kuota VLESS terlampaui untuk '{username}'. Memulai penghapusan permanen.")
    
    for f_path in [
        os.path.join(DIR_DATABASE, f"{username}.txt"),
        os.path.join(DIR_QUOTA_USAGE, username),
        os.path.join(DIR_QUOTA_LIMIT, username)
    ]:
        if os.path.exists(f_path):
            try:
                os.remove(f_path)
            except OSError as e:
                print(f"WARNING: Gagal menghapus file {f_path}: {e}", file=sys.stderr)

    try:
        with open(PATH_CONFIG, 'r') as f: lines = f.readlines()
        
        new_lines = []
        skip_next_line = False
        user_found = False
        for line in lines:
            if skip_next_line:
                skip_next_line = False
                continue
            if line.strip().startswith(f'#@ {username}'):
                skip_next_line = True
                user_found = True
                continue
            new_lines.append(line)
        
        if user_found:
            full_config = "".join(new_lines)
            full_config = re.sub(r',\s*\n(\s*})', r'\n\1', full_config)
            with open(PATH_CONFIG, 'w') as f: f.write(full_config)
            print(f"INFO: Berhasil menghapus '{username}' dari {PATH_CONFIG}")
            
            send_telegram_notification(username)
            return True
    except Exception as e:
        print(f"ERROR: Gagal memodifikasi {PATH_CONFIG}: {e}", file=sys.stderr)
    
    return False

def main():
    os.makedirs(DIR_QUOTA_USAGE, exist_ok=True)
    os.makedirs(DIR_QUOTA_LIMIT, exist_ok=True)
    
    users = get_all_users()
    if not users:
        print("INFO: Tidak ada user VLESS yang ditemukan untuk dicek.")
        return

    config_changed = False
    
    for user in users:
        if not os.path.exists(os.path.join(DIR_QUOTA_LIMIT, user)): continue

        downlink = 0
        try:
            api_cmd = ["xray", "api", "stats", "--server=127.0.0.1:10085", "-name", f"user>>>{user}>>>traffic>>>downlink"]
            result = subprocess.run(api_cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0 and result.stdout:
                stats = json.loads(result.stdout)
                downlink = int(stats['stat']['value'])
            
            if downlink > 0:
                usage_file = os.path.join(DIR_QUOTA_USAGE, user)
                total_usage = downlink
                if os.path.exists(usage_file):
                    with open(usage_file, 'r') as f:
                        total_usage += int(f.read().strip())
                
                with open(usage_file, 'w') as f: f.write(str(total_usage))
                
                subprocess.run(api_cmd + ["-reset"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"WARNING: Gagal memproses statistik untuk '{user}': {e}", file=sys.stderr)
            continue
            
    for user in users:
        limit_file = os.path.join(DIR_QUOTA_LIMIT, user)
        usage_file = os.path.join(DIR_QUOTA_USAGE, user)
        
        if os.path.exists(limit_file) and os.path.exists(usage_file):
            try:
                with open(limit_file, 'r') as f: limit_bytes = int(f.read().strip())
                with open(usage_file, 'r') as f: usage_bytes = int(f.read().strip())
                
                if limit_bytes > 0 and usage_bytes >= limit_bytes:
                    if delete_user_permanently(user):
                        config_changed = True
            except (IOError, ValueError) as e:
                print(f"WARNING: Gagal memeriksa kuota untuk '{user}': {e}", file=sys.stderr)

    if config_changed:
        print("INFO: Konfigurasi berubah. Me-restart layanan Xray...")
        try:
            subprocess.run(["systemctl", "restart", "xray.service"], check=True)
            print("INFO: Layanan Xray berhasil di-restart.")
        except subprocess.CalledProcessError as e:
            print(f"ERROR: Gagal me-restart layanan Xray: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
