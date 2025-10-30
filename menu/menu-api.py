#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import secrets
import string

# --- Konfigurasi ---
API_KEY_FILE = "/etc/api/key"
API_DIR = "/etc/api"
SERVICE_NAME = "server.service"
DOMAIN_FILE = "/etc/xray/domain"

# --- UI & Warna ---
class Colors:
    RED = '\033[1;31m'
    GREEN = '\033[1;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[1;34m'
    CYAN = '\033[1;36m'
    NC = '\033[0m'
    BOLD = '\033[1m'

# --- Fungsi Bantuan ---

def clear_screen():
    """Membersihkan layar terminal."""
    os.system('cls' if os.name == 'nt' else 'clear')

def press_enter_to_continue():
    """Menjeda eksekusi hingga pengguna menekan Enter."""
    input(f"\n{Colors.YELLOW}Tekan Enter untuk kembali ke menu...{Colors.NC}")

def loading_animation(message):
    """Menampilkan animasi loading sederhana."""
    print(f"{Colors.CYAN}{message}{Colors.NC}", end="", flush=True)
    for _ in range(3):
        print(".", end="", flush=True)
        time.sleep(0.4)
    print()

def run_systemctl(*actions):
    """Menjalankan satu atau lebih perintah systemctl dengan aman."""
    for action in actions:
        try:
            subprocess.run(["systemctl", action, SERVICE_NAME], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"{Colors.RED}Error saat menjalankan 'systemctl {action}': {e.stderr.decode()}{Colors.NC}")
            return False
    return True

def get_service_status():
    """Mendapatkan status layanan server.service."""
    try:
        result = subprocess.run(["systemctl", "is-active", SERVICE_NAME], capture_output=True, text=True)
        if result.stdout.strip() == "active":
            return f"{Colors.GREEN}● ONLINE{Colors.NC}"
        else:
            return f"{Colors.RED}● OFFLINE{Colors.NC}"
    except Exception:
        return f"{Colors.RED}● ERROR{Colors.NC}"

# --- Fungsi Menu ---

def generate_new_key():
    """1. Generate New Key Token"""
    clear_screen()
    loading_animation("Menciptakan token baru")
    
    # Membuat token alfanumerik 32 karakter yang aman
    alphabet = string.ascii_letters + string.digits
    new_key = "rerechan_" + ''.join(secrets.choice(alphabet) for _ in range(32))
    
    try:
        os.makedirs(API_DIR, exist_ok=True)
        # Baca keys yang ada untuk menghindari duplikasi
        existing_keys = []
        if os.path.exists(API_KEY_FILE):
            with open(API_KEY_FILE, 'r') as f:
                existing_keys = f.read().splitlines()
        
        if new_key not in existing_keys:
            with open(API_KEY_FILE, 'a') as f:
                f.write(new_key + '\n')
        
        # Cukup restart service untuk memuat token baru
        run_systemctl("restart")

        clear_screen()
        print(f"{Colors.GREEN}{Colors.BOLD}✔ Berhasil Membuat Token Baru{Colors.NC}")
        print(f"{Colors.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.NC}")
        print(f"{Colors.YELLOW}Token API Anda:{Colors.NC}")
        print(f"{Colors.BOLD}{new_key}{Colors.NC}")
        print(f"{Colors.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.NC}")
    except Exception as e:
        print(f"{Colors.RED}Gagal membuat token: {e}{Colors.NC}")

def add_manual_key():
    """3. Add Key Token API"""
    clear_screen()
    print(f"{Colors.YELLOW}Tambah Token API Manual{Colors.NC}")
    print(f"{Colors.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.NC}")
    token = input("Masukkan Token: ").strip()
    
    if not token:
        print(f"{Colors.RED}Token tidak boleh kosong.{Colors.NC}")
        return

    loading_animation("Menambahkan token")
    try:
        os.makedirs(API_DIR, exist_ok=True)
        with open(API_KEY_FILE, 'a') as f:
            f.write(token + '\n')
        
        run_systemctl("restart")

        clear_screen()
        print(f"{Colors.GREEN}{Colors.BOLD}✔ Berhasil Menambah Key API{Colors.NC}")
        with open(API_KEY_FILE, 'r') as f:
            all_keys = f.read()
        print(f"{Colors.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.NC}")
        print(f"{Colors.YELLOW}Semua Token API Aktif:{Colors.NC}")
        print(f"{Colors.BOLD}{all_keys}{Colors.NC}")
        print(f"{Colors.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.NC}")
    except Exception as e:
        print(f"{Colors.RED}Gagal menambah token: {e}{Colors.NC}")

def edit_key_file():
    """2. Change Manual Key Token"""
    clear_screen()
    print("Membuka editor 'nano' untuk mengedit file token...")
    time.sleep(1)
    subprocess.run(["nano", API_KEY_FILE])
    loading_animation("Me-restart API setelah edit")
    run_systemctl("restart")
    print(f"{Colors.GREEN}API berhasil di-restart.{Colors.NC}")

def enable_api():
    """4. Enable API"""
    clear_screen()
    loading_animation("Mengaktifkan API")
    subprocess.run(["systemctl", "daemon-reload"], capture_output=True)
    if run_systemctl("enable", "start"):
        print(f"{Colors.GREEN}{Colors.BOLD}✔ API Berhasil Diaktifkan{Colors.NC}")

def restart_api():
    """5. Restart API"""
    clear_screen()
    loading_animation("Me-restart API")
    if run_systemctl("restart"):
        print(f"{Colors.GREEN}{Colors.BOLD}✔ API Berhasil Di-restart{Colors.NC}")

def disable_api():
    """6. Disable API"""
    clear_screen()
    loading_animation("Menonaktifkan API")
    if run_systemctl("stop", "disable"):
        print(f"{Colors.RED}{Colors.BOLD}✖ API Berhasil Dinonaktifkan{Colors.NC}")

# --- Loop Menu Utama ---
def main():
    """Menampilkan menu utama dan mengatur alur program."""
    if os.geteuid() != 0:
        print(f"{Colors.RED}Error: Skrip ini harus dijalankan dengan hak akses root (sudo).{Colors.NC}")
        sys.exit(1)

    while True:
        clear_screen()
        status = get_service_status()
        domain = "domain_not_set"
        if os.path.exists(DOMAIN_FILE):
            with open(DOMAIN_FILE, 'r') as f:
                domain = f.read().strip()

        menu_text = f"""
{Colors.BOLD}{Colors.BLUE}╔════════════════════════════════════════════╗{Colors.NC}
{Colors.BOLD}{Colors.BLUE}║             {Colors.CYAN}<= Menu Web API =>             {Colors.BLUE}║{Colors.NC}
{Colors.BOLD}{Colors.BLUE}╠════════════════════════════════════════════╣{Colors.NC}
{Colors.BOLD}{Colors.BLUE}║{Colors.NC}  {Colors.YELLOW}Status: {status}
{Colors.BOLD}{Colors.BLUE}║{Colors.NC}  {Colors.CYAN}Domain: {Colors.BOLD}{domain}{Colors.NC}
{Colors.BOLD}{Colors.BLUE}╠════════════════════════════════════════════╣{Colors.NC}
{Colors.BOLD}{Colors.BLUE}║{Colors.NC}  {Colors.YELLOW}Contoh Endpoint:{Colors.NC}
{Colors.BOLD}{Colors.BLUE}║{Colors.NC}    - https://{domain}/api/add-trojan
{Colors.BOLD}{Colors.BLUE}║{Colors.NC}    - http://{domain}:9000/add-trojan
{Colors.BOLD}{Colors.BLUE}╠════════════════════════════════════════════╣{Colors.NC}
{Colors.BOLD}{Colors.BLUE}║{Colors.NC}  {Colors.BOLD}1.{Colors.NC} Generate Token Baru      {Colors.CYAN}- Otomatis buat token baru{Colors.NC}
{Colors.BOLD}{Colors.BLUE}║{Colors.NC}  {Colors.BOLD}2.{Colors.NC} Edit File Token          {Colors.CYAN}- Edit file token via nano{Colors.NC}
{Colors.BOLD}{Colors.BLUE}║{Colors.NC}  {Colors.BOLD}3.{Colors.NC} Tambah Token Manual      {Colors.CYAN}- Tambah satu token manual{Colors.NC}
{Colors.BOLD}{Colors.BLUE}║{Colors.NC}  {Colors.BOLD}4.{Colors.NC} Aktifkan API             {Colors.CYAN}- Enable & start service{Colors.NC}
{Colors.BOLD}{Colors.BLUE}║{Colors.NC}  {Colors.BOLD}5.{Colors.NC} Restart API              {Colors.CYAN}- Restart service API{Colors.NC}
{Colors.BOLD}{Colors.BLUE}║{Colors.NC}  {Colors.BOLD}6.{Colors.NC} Nonaktifkan API          {Colors.CYAN}- Stop & disable service{Colors.NC}
{Colors.BOLD}{Colors.BLUE}║{Colors.NC}  {Colors.BOLD}0.{Colors.NC} Keluar                   {Colors.CYAN}- Keluar dari menu ini{Colors.NC}
{Colors.BOLD}{Colors.BLUE}╚════════════════════════════════════════════╝{Colors.NC}
"""
        print(menu_text)
        
        choice = input(f"{Colors.YELLOW}Pilih Opsi [0-6]: {Colors.NC}").strip()

        if choice == '1':
            generate_new_key()
            press_enter_to_continue()
        elif choice == '2':
            edit_key_file()
            press_enter_to_continue()
        elif choice == '3':
            add_manual_key()
            press_enter_to_continue()
        elif choice == '4':
            enable_api()
            press_enter_to_continue()
        elif choice == '5':
            restart_api()
            press_enter_to_continue()
        elif choice == '6':
            disable_api()
            press_enter_to_continue()
        elif choice == '0':
            clear_screen()
            print("Keluar dari menu API.")
            break
        else:
            print(f"\n{Colors.RED}Opsi tidak valid!{Colors.NC}")
            time.sleep(1)

if __name__ == "__main__":
    main()
