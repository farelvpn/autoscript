#!/usr/bin/env python3
import os
import sys
import subprocess
import json

# --- Konfigurasi Path & Warna ---
DIR_CONFIG = "/etc/xray"
BOT_KEY_FILE = os.path.join(DIR_CONFIG, "bot.key")
CLIENT_ID_FILE = os.path.join(DIR_CONFIG, "client.id")

# Kode warna untuk terminal
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

# --- Fungsi Bantuan ---

def clear_screen():
    """Membersihkan layar terminal."""
    os.system('cls' if os.name == 'nt' else 'clear')

def press_enter_to_continue():
    """Menjeda eksekusi hingga pengguna menekan Enter."""
    input(f"\n{Colors.YELLOW}Tekan Enter untuk melanjutkan...{Colors.END}")

def get_current_config():
    """Membaca dan mengembalikan konfigurasi yang ada saat ini."""
    token = ""
    chat_id = ""
    try:
        if os.path.exists(BOT_KEY_FILE):
            with open(BOT_KEY_FILE, 'r') as f:
                token = f.read().strip()
        if os.path.exists(CLIENT_ID_FILE):
            with open(CLIENT_ID_FILE, 'r') as f:
                chat_id = f.read().strip()
    except Exception as e:
        print(f"{Colors.RED}Error membaca file konfigurasi: {e}{Colors.END}")
    return token, chat_id

# --- Fungsi Menu Utama ---

def add_credentials():
    """1. Menambahkan data untuk telegram id & bot token."""
    clear_screen()
    print(f"{Colors.BLUE}{Colors.BOLD}---[ 1. Tambah Kredensial Telegram ]---{Colors.END}\n")
    
    try:
        # Membuat direktori jika belum ada
        os.makedirs(DIR_CONFIG, exist_ok=True)
        
        bot_token = input(f"Masukkan Bot Token Anda: {Colors.GREEN}").strip()
        if not bot_token:
            print(f"\n{Colors.RED}Bot Token tidak boleh kosong.{Colors.END}")
            return

        chat_id = input(f"{Colors.END}Masukkan Chat ID Admin: {Colors.GREEN}").strip()
        if not chat_id:
            print(f"\n{Colors.RED}Chat ID tidak boleh kosong.{Colors.END}")
            return

        with open(BOT_KEY_FILE, 'w') as f:
            f.write(bot_token)
        with open(CLIENT_ID_FILE, 'w') as f:
            f.write(chat_id)
            
        print(f"\n{Colors.GREEN}{Colors.BOLD}Sukses! Kredensial Telegram berhasil disimpan.{Colors.END}")

    except PermissionError:
        print(f"\n{Colors.RED}{Colors.BOLD}Error: Izin ditolak!{Colors.END}")
        print(f"{Colors.YELLOW}Pastikan Anda menjalankan skrip ini dengan 'sudo'.{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Terjadi kesalahan: {e}{Colors.END}")

def manage_credentials():
    """2. Menghapus & Mengganti detail data telegram."""
    while True:
        clear_screen()
        token, chat_id = get_current_config()
        
        print(f"{Colors.BLUE}{Colors.BOLD}---[ 2. Kelola Kredensial Telegram ]---{Colors.END}\n")
        print(f"Token Saat Ini : {Colors.GREEN}{token or 'Belum diatur'}{Colors.END}")
        print(f"Chat ID Saat Ini: {Colors.GREEN}{chat_id or 'Belum diatur'}{Colors.END}\n")
        
        print("1. Ganti Bot Token")
        print("2. Ganti Chat ID")
        print(f"{Colors.RED}3. Hapus Semua Kredensial{Colors.END}")
        print("0. Kembali ke Menu Utama")
        
        choice = input("\nPilih opsi: ").strip()

        try:
            if choice == '1':
                new_token = input(f"\nMasukkan Bot Token baru: {Colors.GREEN}").strip()
                if new_token:
                    with open(BOT_KEY_FILE, 'w') as f: f.write(new_token)
                    print(f"\n{Colors.GREEN}Bot Token berhasil diganti.{Colors.END}")
                else:
                    print(f"\n{Colors.RED}Input tidak boleh kosong.{Colors.END}")
                press_enter_to_continue()
            elif choice == '2':
                new_chat_id = input(f"\n{Colors.END}Masukkan Chat ID baru: {Colors.GREEN}").strip()
                if new_chat_id:
                    with open(CLIENT_ID_FILE, 'w') as f: f.write(new_chat_id)
                    print(f"\n{Colors.GREEN}Chat ID berhasil diganti.{Colors.END}")
                else:
                    print(f"\n{Colors.RED}Input tidak boleh kosong.{Colors.END}")
                press_enter_to_continue()
            elif choice == '3':
                confirm = input(f"\n{Colors.YELLOW}Anda yakin ingin menghapus semua kredensial? (y/n): {Colors.END}").lower()
                if confirm == 'y':
                    if os.path.exists(BOT_KEY_FILE): os.remove(BOT_KEY_FILE)
                    if os.path.exists(CLIENT_ID_FILE): os.remove(CLIENT_ID_FILE)
                    print(f"\n{Colors.GREEN}Semua kredensial berhasil dihapus.{Colors.END}")
                else:
                    print("\nPenghapusan dibatalkan.")
                press_enter_to_continue()
            elif choice == '0':
                break
            else:
                print(f"\n{Colors.RED}Pilihan tidak valid.{Colors.END}")
                press_enter_to_continue()

        except PermissionError:
            print(f"\n{Colors.RED}{Colors.BOLD}Error: Izin ditolak! Jalankan dengan 'sudo'.{Colors.END}")
            press_enter_to_continue()
        except Exception as e:
            print(f"\n{Colors.RED}Terjadi kesalahan: {e}{Colors.END}")
            press_enter_to_continue()

def validate_credentials():
    """3. Mengecek validitas Bot Token dan Chat ID."""
    clear_screen()
    print(f"{Colors.BLUE}{Colors.BOLD}---[ 3. Validasi Kredensial Telegram ]---{Colors.END}\n")
    token, chat_id = get_current_config()

    if not token:
        print(f"{Colors.RED}Bot Token belum diatur. Silakan tambahkan melalui menu 1.{Colors.END}")
        return

    # Validasi Bot Token
    print("Mengecek Bot Token...", end="", flush=True)
    try:
        cmd = ["curl", "-s", f"https://api.telegram.org/bot{token}/getMe"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        response = json.loads(result.stdout)
        
        if response.get("ok"):
            bot_name = response.get("result", {}).get("first_name", "N/A")
            bot_username = response.get("result", {}).get("username", "N/A")
            print(f" {Colors.GREEN}VALID{Colors.END}")
            print(f"  - Nama Bot: {Colors.BOLD}{bot_name}{Colors.END}")
            print(f"  - Username: {Colors.BOLD}@{bot_username}{Colors.END}")
            token_valid = True
        else:
            error_desc = response.get("description", "Unknown error")
            print(f" {Colors.RED}TIDAK VALID{Colors.END}")
            print(f"  - Alasan: {error_desc}")
            token_valid = False

    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
        print(f" {Colors.RED}ERROR{Colors.END}")
        print(f"  - Tidak dapat terhubung ke API Telegram atau respons tidak valid.")
        token_valid = False

    # Validasi Chat ID (hanya jika token valid dan chat_id ada)
    if token_valid and chat_id:
        print("\nMengecek Chat ID...", end="", flush=True)
        try:
            cmd = ["curl", "-s", f"https://api.telegram.org/bot{token}/getChat?chat_id={chat_id}"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            response = json.loads(result.stdout)

            if response.get("ok"):
                chat_title = response.get("result", {}).get("title") or response.get("result", {}).get("first_name", "N/A")
                chat_type = response.get("result", {}).get("type", "N/A")
                print(f" {Colors.GREEN}VALID{Colors.END}")
                print(f"  - Nama Chat: {Colors.BOLD}{chat_title}{Colors.END}")
                print(f"  - Tipe Chat: {Colors.BOLD}{chat_type}{Colors.END}")
            else:
                error_desc = response.get("description", "Unknown error")
                print(f" {Colors.RED}TIDAK VALID{Colors.END}")
                print(f"  - Alasan: {error_desc}")

        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
            print(f" {Colors.RED}ERROR{Colors.END}")
            print(f"  - Tidak dapat terhubung atau memvalidasi Chat ID.")
    elif not chat_id:
        print(f"\n{Colors.YELLOW}Chat ID belum diatur.{Colors.END}")

# --- Loop Menu Utama ---
def main():
    """Menampilkan menu utama dan mengatur alur program."""
    if os.geteuid() != 0:
        print(f"{Colors.RED}{Colors.BOLD}Error: Skrip ini memerlukan akses root.{Colors.END}")
        print(f"{Colors.YELLOW}Silakan jalankan dengan 'sudo telegram-config'{Colors.END}")
        sys.exit(1)
        
    while True:
        clear_screen()
        token, chat_id = get_current_config()
        print(f"{Colors.BOLD}========================================={Colors.END}")
        print(f"{Colors.BLUE}{Colors.BOLD}  Menu Konfigurasi Telegram Bot Notifier {Colors.END}")
        print(f"{Colors.BOLD}========================================={Colors.END}\n")
        print(f"Status Saat Ini:")
        print(f"  - Bot Token: {Colors.GREEN}{'Terisi' if token else f'{Colors.RED}Kosong'}{Colors.END}")
        print(f"  - Chat ID  : {Colors.GREEN}{'Terisi' if chat_id else f'{Colors.RED}Kosong'}{Colors.END}\n")
        
        print("1. Tambah Kredensial (Token & Chat ID)")
        print("2. Kelola Kredensial (Ganti / Hapus)")
        print("3. Validasi Kredensial Saat Ini")
        print(f"0. Keluar")
        
        choice = input("\nPilih opsi: ").strip()
        
        if choice == '1':
            add_credentials()
            press_enter_to_continue()
        elif choice == '2':
            manage_credentials()
        elif choice == '3':
            validate_credentials()
            press_enter_to_continue()
        elif choice == '0':
            print("\nKeluar dari program. Sampai jumpa!")
            break
        else:
            print(f"\n{Colors.RED}Pilihan tidak valid, silakan coba lagi.{Colors.END}")
            press_enter_to_continue()

if __name__ == "__main__":
    main()
