#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import random
import string

# --- Konfigurasi ---
DOMAIN_FILE = "/etc/xray/domain"
CERT_CRT_FILE = "/etc/xray/xray.crt"
CERT_KEY_FILE = "/etc/xray/xray.key"
NGINX_CONF_FILE = "/etc/nginx/fn.conf" # Asumsi dari skrip bash
ACME_SH_PATH = os.path.expanduser("~/.acme.sh/acme.sh")

# --- UI & Warna ---
class Colors:
    RED = '\033[0;91m'
    GREEN = '\033[0;92m'
    YELLOW = '\033[0;93m'
    NC = '\033[0m'

# --- Fungsi Bantuan ---

def clear_screen():
    """Membersihkan layar terminal."""
    os.system('cls' if os.name == 'nt' else 'clear')

def press_enter_to_continue(message="Tekan Enter untuk kembali ke menu"):
    """Menjeda eksekusi hingga pengguna menekan Enter."""
    input(f"\n{Colors.YELLOW}{message}...{Colors.NC}")

def run_command(command, shell=False):
    """Menjalankan perintah dan menangani error."""
    try:
        subprocess.run(command, check=True, shell=shell, stdout=sys.stdout, stderr=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(f"\n{Colors.RED}Error saat menjalankan perintah: {e}{Colors.NC}")
        press_enter_to_continue()
        return False
    return True

# --- Logika Inti ---

def install_acme():
    """Memeriksa dan menginstal acme.sh jika belum ada, lalu mendaftarkan akun."""
    if not os.path.exists(ACME_SH_PATH):
        print(f"[{Colors.YELLOW}INFO{Colors.NC}] acme.sh tidak ditemukan, proses instalasi...")
        # Perintah `curl | sh` harus dijalankan dengan shell=True
        run_command("curl https://get.acme.sh | sh", shell=True)

    acme_account_conf = os.path.expanduser("~/.acme.sh/account.conf")
    if not os.path.exists(acme_account_conf):
        random_prefix = ''.join(random.choices(string.ascii_lowercase, k=5))
        random_number = random.randint(1000, 9999)
        acme_email = f"{random_prefix}{random_number}@rerechan.biz.id"
        print(f"[{Colors.GREEN}INFO{Colors.NC}] Mendaftarkan akun baru dengan email: {acme_email}")
        # Menjalankan perintah acme.sh dengan path absolut
        run_command([ACME_SH_PATH, "--register-account", "-m", acme_email, "--agree-tos"])
    else:
        print(f"[{Colors.GREEN}INFO{Colors.NC}] Akun ACME sudah ada. Menggunakan yang sudah ada.")

def renew_certificate():
    """2. Renew Certificate Your Domain"""
    clear_screen()
    print("Memulai proses perpanjangan sertifikat...")
    
    install_acme()

    try:
        with open(DOMAIN_FILE, 'r') as f:
            domain = f.read().strip()
    except FileNotFoundError:
        print(f"{Colors.RED}Error: File domain '{DOMAIN_FILE}' tidak ditemukan.{Colors.NC}")
        return

    print(f"[{Colors.GREEN}INFO{Colors.NC}] Menghentikan layanan Nginx...")
    run_command(["systemctl", "stop", "nginx"])

    # Hapus sertifikat lama jika ada
    for cert_file in [CERT_CRT_FILE, CERT_KEY_FILE]:
        if os.path.exists(cert_file):
            os.remove(cert_file)

    print(f"[{Colors.GREEN}INFO{Colors.NC}] Memproses sertifikat baru untuk domain: {domain}")
    
    # Menjalankan perintah acme.sh
    run_command([ACME_SH_PATH, "--set-default-ca", "--server", "letsencrypt"])
    run_command([ACME_SH_PATH, "--issue", "-d", domain, "--standalone", "-k", "ec-256"])
    run_command([
        ACME_SH_PATH, "--installcert", "-d", domain,
        "--fullchainpath", CERT_CRT_FILE,
        "--keypath", CERT_KEY_FILE,
        "--ecc"
    ])
    
    print(f"\n[{Colors.GREEN}INFO{Colors.NC}] Sertifikat berhasil diperbarui.")
    print(f"[{Colors.GREEN}INFO{Colors.NC}] Me-restart layanan Nginx...")
    run_command(["systemctl", "restart", "nginx"])
    
    print(f"\n{Colors.GREEN}Semua proses selesai.{Colors.NC}")
    press_enter_to_continue("Tekan Enter untuk kembali")

def change_domain():
    """1. Change Hostname/Domain"""
    clear_screen()
    current_domain = ""
    try:
        with open(DOMAIN_FILE, 'r') as f:
            current_domain = f.read().strip()
    except FileNotFoundError:
        print(f"[{Colors.YELLOW}INFO{Colors.NC}] File domain belum ada.")
    
    print(f"\033[0;93m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m")
    print("Domain Anda saat ini:")
    print(f"{Colors.GREEN}{current_domain or 'Belum diatur'}{Colors.NC}")
    print()
    new_host = input("Masukkan Domain/Host baru (biarkan kosong untuk batal): ").strip()
    
    if not new_host:
        print("\nPerubahan domain dibatalkan.")
        return
    
    try:
        # Mengganti domain di file Nginx config
        if current_domain and os.path.exists(NGINX_CONF_FILE):
            with open(NGINX_CONF_FILE, 'r') as f:
                config_content = f.read()
            
            config_content = config_content.replace(
                f"server_name {current_domain};",
                f"server_name {new_host};"
            )

            with open(NGINX_CONF_FILE, 'w') as f:
                f.write(config_content)
        
        # Menulis domain baru ke file domain
        with open(DOMAIN_FILE, 'w') as f:
            f.write(new_host)

        print(f"\n{Colors.GREEN}Domain berhasil diubah menjadi: {new_host}{Colors.NC}")
        press_enter_to_continue("Tekan Enter untuk melanjutkan ke perpanjangan sertifikat")
        renew_certificate()

    except PermissionError:
        print(f"\n{Colors.RED}Error: Izin ditolak. Jalankan skrip ini dengan 'sudo'.{Colors.NC}")
    except Exception as e:
        print(f"\n{Colors.RED}Terjadi kesalahan: {e}{Colors.NC}")


# --- Loop Menu Utama ---
def main():
    """Menampilkan menu utama dan mengatur alur program."""
    if os.geteuid() != 0:
        print(f"{Colors.RED}Error: Skrip ini harus dijalankan dengan hak akses root (sudo).{Colors.NC}")
        sys.exit(1)
        
    while True:
        clear_screen()
        print("\033[0;93m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m")
        print(" 1. Ubah Hostname/Domain Server")
        print(" 2. Perbarui Sertifikat Domain")
        print(" 0. Keluar")
        print("\033[0;93m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m")
        
        choice = input("Pilih Opsi: ").strip()
        
        if choice == '1':
            change_domain()
            press_enter_to_continue()
        elif choice == '2':
            renew_certificate()
        elif choice == '0':
            clear_screen()
            print("Keluar dari menu.")
            break
        else:
            print(f"\n{Colors.RED}Pilihan tidak valid.{Colors.NC}")
            time.sleep(1)

if __name__ == "__main__":
    main()
