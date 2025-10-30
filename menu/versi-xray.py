#!/usr/bin/env python3
import os
import sys
import shutil
import platform
import subprocess
import requests
import zipfile
import tempfile
import re

# --- Definisi Warna ANSI ---
class Color:
    NC = '\033[0m'
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    CYAN = '\033[0;36m'
    BICyan = '\033[1;96m'
    BIWhite = '\033[1;97m'
    BLUE_BG = '\033[0;34m'
    HEADER_BG = '\033[0;41;36m'

def print_header():
    """Mencetak header skrip yang bergaya."""
    clear_screen()
    line = f"{Color.BLUE_BG}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Color.NC}"
    print(line)
    print(f"{Color.HEADER_BG}           XRAY CORE VERSION CHANGER           {Color.NC}")
    print(line)

def clear_screen():
    """Membersihkan layar terminal."""
    os.system('cls' if os.name == 'nt' else 'clear')

def run_command(command):
    """Menjalankan perintah shell dan mengembalikan outputnya."""
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

def get_architecture():
    """Mendeteksi arsitektur sistem dan memetakannya ke format unduhan."""
    arch_map = {
        'x86_64': '64',
        'aarch64': 'arm64-v8a',
        'armv7l': 'arm32-v7a'
    }
    system_arch = platform.machine()
    download_arch = arch_map.get(system_arch)
    return system_arch, download_arch

def wait_for_key():
    """Menunggu pengguna menekan tombol apa saja."""
    print()
    input(f"{Color.CYAN}Tekan Enter untuk kembali ke menu...{Color.NC}")

def main():
    """Fungsi utama untuk menjalankan skrip."""
    print_header()

    # 1. Temukan path Xray
    xray_path = shutil.which('xray')
    if not xray_path:
        print(f"{Color.RED}Error: Xray tidak ditemukan di sistem!{Color.NC}")
        wait_for_key()
        sys.exit(1)

    print(f"{Color.BIWhite}Lokasi Xray Saat Ini:{Color.NC} {Color.GREEN}{xray_path}{Color.NC}")

    # 2. Deteksi Arsitektur
    system_arch, download_arch = get_architecture()
    if not download_arch:
        print(f"{Color.RED}Arsitektur tidak didukung: {system_arch}{Color.NC}")
        wait_for_key()
        sys.exit(1)
        
    print(f"{Color.BIWhite}Arsitektur Sistem    :{Color.NC} {Color.GREEN}{system_arch}{Color.NC}")
    print(f"{Color.BIWhite}Arsitektur Unduhan   :{Color.NC} {Color.GREEN}{download_arch}{Color.NC}")
    
    # 3. Dapatkan Versi Saat Ini
    version_output = run_command([xray_path, 'version'])
    current_version = version_output.split('\n')[0].split(' ')[1] if version_output else "Tidak diketahui"
    print(f"{Color.BIWhite}Versi Saat Ini       :{Color.NC} {Color.GREEN}{current_version}{Color.NC}")
    
    line = f"{Color.BLUE_BG}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Color.NC}"
    print(line)

    # 4. Tampilkan Menu Pilihan Versi
    versions = [
        "v1.8.4", "v1.8.5", "v1.8.6", "v1.8.9", "v1.8.10", "v1.8.12",
        "v1.8.15", "v1.8.20", "v1.8.25", "v25.3.6", "v25.7.24", "v25.7.25",
        "v25.7.26", "v25.8.3"
    ]
    
    print(f"{Color.BICyan}Versi Xray Core yang Tersedia:{Color.NC}")
    print(line)
    for i, ver in enumerate(versions, 1):
        print(f"{i}.  Xray {ver}")
    print("15. Versi Kustom (Masukkan manual)")
    print("0.  Batal")
    print(line)

    # 5. Dapatkan Input Pengguna
    try:
        choice = int(input("Pilih versi (0-15): "))
        if 1 <= choice <= len(versions):
            selected_version = versions[choice - 1]
        elif choice == 15:
            selected_version = input("Masukkan versi (misal, v1.8.9): ")
            if not re.match(r'^v\d+\.\d+\.\d+$', selected_version):
                print(f"\n{Color.RED}Format versi tidak valid! Gunakan format seperti v1.8.9{Color.NC}")
                wait_for_key()
                sys.exit(1)
        elif choice == 0:
            print(f"\n{Color.YELLOW}Operasi dibatalkan.{Color.NC}")
            sys.exit(0)
        else:
            raise ValueError
    except ValueError:
        print(f"\n{Color.RED}Pilihan tidak valid. Keluar.{Color.NC}")
        sys.exit(1)

    print(f"\n{Color.BIWhite}Versi yang Dipilih:{Color.NC} {Color.GREEN}{selected_version}{Color.NC}\n")

    # 6. Konfirmasi
    confirm = input(f"{Color.RED}Apakah Anda yakin ingin memperbarui Xray core? (y/N): {Color.NC}").lower()
    if confirm not in ['y', 'yes']:
        print(f"\n{Color.YELLOW}Operasi dibatalkan.{Color.NC}")
        sys.exit(0)

    # --- Proses Pembaruan ---
    print()
    backup_path = f"{xray_path}.backup"
    
    try:
        # Stop service & backup
        print(f"{Color.YELLOW}Menghentikan layanan Xray...{Color.NC}")
        run_command(['systemctl', 'stop', 'xray.service'])
        
        print(f"{Color.YELLOW}Membuat backup Xray core saat ini...{Color.NC}")
        shutil.copy(xray_path, backup_path)

        # Download di direktori sementara
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, 'xray.zip')
            download_url = f"https://github.com/XTLS/Xray-core/releases/download/{selected_version}/Xray-linux-{download_arch}.zip"
            
            print(f"{Color.YELLOW}Mengunduh Xray {selected_version} untuk {system_arch}...{Color.NC}")
            response = requests.get(download_url, stream=True)
            response.raise_for_status() # Error jika status code bukan 2xx
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"{Color.YELLOW}Mengekstrak dan memasang core baru...{Color.NC}")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extract('xray', temp_dir)

            new_xray_path = os.path.join(temp_dir, 'xray')
            os.chmod(new_xray_path, 0o755) # Memberikan izin eksekusi (rwxr-xr-x)
            
            # Ganti core lama dengan yang baru
            shutil.move(new_xray_path, xray_path)

    except Exception as e:
        print(f"\n{Color.RED}Error terjadi: {e}{Color.NC}")
        print(f"{Color.YELLOW}Mengembalikan backup...{Color.NC}")
        if os.path.exists(backup_path):
            shutil.move(backup_path, xray_path)
        print(f"{Color.YELLOW}Menjalankan kembali layanan Xray...{Color.NC}")
        run_command(['systemctl', 'start', 'xray.service'])
        wait_for_key()
        sys.exit(1)
    
    # Hapus backup jika berhasil
    if os.path.exists(backup_path):
        os.remove(backup_path)

    # Mulai kembali layanan
    print(f"{Color.YELLOW}Menjalankan layanan Xray...{Color.NC}")
    run_command(['systemctl', 'start', 'xray.service'])
    
    # Verifikasi
    new_version_output = run_command([xray_path, 'version'])
    new_version = new_version_output.split('\n')[0].split(' ')[1] if new_version_output else "Gagal verifikasi"
    
    print(line)
    if selected_version in new_version:
        print(f"{Color.GREEN}SUKSES:{Color.NC} {Color.BIWhite}Xray core diperbarui ke {Color.GREEN}{new_version}{Color.NC}")
        print(f"{Color.BIWhite}Versi Sebelumnya:{Color.NC} {Color.RED}{current_version}{Color.NC}")
        print(f"{Color.BIWhite}Versi Saat Ini  :{Color.NC} {Color.GREEN}{new_version}{Color.NC}")
    else:
        print(f"{Color.YELLOW}PERINGATAN:{Color.NC} {Color.BIWhite}Verifikasi versi gagal{Color.NC}")
        print(f"{Color.BIWhite}Versi Diharapkan:{Color.NC} {Color.GREEN}{selected_version}{Color.NC}")
        print(f"{Color.BIWhite}Versi Saat Ini  :{Color.NC} {Color.GREEN}{new_version}{Color.NC}")
    
    print(line)
    print(f"{Color.GREEN}✓{Color.NC} {Color.BIWhite}Config.json tidak diubah{Color.NC}")
    print(f"{Color.GREEN}✓{Color.NC} {Color.BIWhite}Konfigurasi layanan tidak diubah{Color.NC}")
    print(f"{Color.GREEN}✓{Color.NC} {Color.BIWhite}File log tidak diubah{Color.NC}")
    print(f"{Color.GREEN}✓{Color.NC} {Color.BIWhite}Hanya file binary core yang diganti{Color.NC}")
    print(line)

    wait_for_key()


if __name__ == "__main__":
    # Pastikan library 'requests' terinstal
    try:
        import requests
    except ImportError:
        print("Library 'requests' tidak ditemukan.")
        print("Silakan instal dengan: pip install requests")
        sys.exit(1)
    
    main()
