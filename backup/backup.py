#!/usr/bin/env python3

import os
import sys
import subprocess
import zipfile
from datetime import datetime

# --- Konfigurasi ---
SOURCE_DIR = "/etc/xray"
BACKUP_TEMP_DIR = "/tmp/xray_backup"
TELEGRAM_BOT_KEY_FILE = os.path.join(SOURCE_DIR, "bot.key")
TELEGRAM_CLIENT_ID_FILE = os.path.join(SOURCE_DIR, "client.id")

# --- Fungsi Bantuan ---

def get_config_value(file_path):
    """Membaca file konfigurasi dengan aman."""
    try:
        with open(file_path, 'r') as f:
            return f.read().strip()
    except Exception:
        return None

def send_telegram_document(bot_token, chat_id, file_path, caption):
    """Mengirim file sebagai dokumen ke Telegram menggunakan curl."""
    print(f"Mengirim {os.path.basename(file_path)} ke Telegram...")
    try:
        result = subprocess.run(
            [
                "curl", "-s",
                "-F", f"chat_id={chat_id}",
                "-F", f"document=@{file_path}",
                "-F", f"caption={caption}",
                f"https://api.telegram.org/bot{bot_token}/sendDocument"
            ],
            capture_output=True, text=True, timeout=60
        )
        if '"ok":true' in result.stdout:
            print("Backup berhasil dikirim ke Telegram.")
            return True
        else:
            # Tulis error ke stderr agar bisa ditangkap di log cron
            print(f"Gagal mengirim ke Telegram. Respons: {result.stdout}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"Error saat menjalankan curl: {e}", file=sys.stderr)
        return False

# --- Logika Utama ---

def main():
    """Fungsi utama untuk membuat dan mengirim satu backup."""
    print(f"🚀 Memulai proses backup pada {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    bot_token = get_config_value(TELEGRAM_BOT_KEY_FILE)
    chat_id = get_config_value(TELEGRAM_CLIENT_ID_FILE)

    if not bot_token or not chat_id:
        print("Error: bot.key atau client.id tidak ditemukan/kosong. Proses dihentikan.", file=sys.stderr)
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_filename_zip = f"backup-{timestamp}.zip"
    zip_path = os.path.join(BACKUP_TEMP_DIR, backup_filename_zip)

    try:
        os.makedirs(BACKUP_TEMP_DIR, exist_ok=True)
        
        print(f"Membuat arsip backup: {zip_path}")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(SOURCE_DIR):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, SOURCE_DIR)
                    zipf.write(file_path, arcname)

        caption = f"Backup otomatis konfigurasi Xray\n📅 {timestamp}"
        send_telegram_document(bot_token, chat_id, zip_path, caption)

    except Exception as e:
        print(f"Terjadi error saat membuat backup: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)
            print("File backup sementara telah dihapus.")
    
    print("✅ Proses backup selesai.")

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Error: Skrip ini harus dijalankan dengan hak akses root (sudo).", file=sys.stderr)
        sys.exit(1)
    main()
