#!/usr/bin/env python3
import os
import sys
import zipfile
import glob
from datetime import datetime

# --- Konfigurasi ---
BACKUP_SEARCH_DIR = "/root"
DESTINATION_DIR = "/etc/xray"
PRE_RESTORE_BACKUP_DIR = "/etc/xray_before_restore"

# --- Kode Warna ---
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

# --- Logika Utama ---

def main():
    """Fungsi utama untuk mencari dan merestore backup."""
    if os.geteuid() != 0:
        print(f"{Colors.RED}Error: Skrip ini harus dijalankan dengan hak akses root (sudo).{Colors.END}")
        sys.exit(1)

    print(f"Mencari file backup di direktori: {Colors.YELLOW}{BACKUP_SEARCH_DIR}{Colors.END}")
    
    # Cari file backup-*zip terbaru
    backup_files = glob.glob(os.path.join(BACKUP_SEARCH_DIR, "backup-*.zip"))
    if not backup_files:
        print(f"{Colors.RED}Tidak ada file 'backup-*.zip' yang ditemukan.{Colors.END}")
        sys.exit(1)

    # Temukan file terbaru berdasarkan nama
    latest_backup_file = max(backup_files, key=os.path.getctime)
    print(f"File backup terbaru ditemukan: {Colors.GREEN}{os.path.basename(latest_backup_file)}{Colors.END}")

    # Konfirmasi dari pengguna
    confirm = input(f"\n{Colors.YELLOW}Anda yakin ingin merestore data dari file ini?{Colors.END}\n"
                    f"{Colors.BOLD}PERINGATAN:{Colors.END} Semua file di {DESTINATION_DIR} akan ditimpa.\n"
                    f"Ketik '{Colors.GREEN}restore{Colors.END}' untuk melanjutkan: ")
    
    if confirm.lower() != 'restore':
        print("Restore dibatalkan.")
        sys.exit(0)

    try:
        # 1. Backup konfigurasi saat ini sebelum ditimpa
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        pre_restore_path = f"{PRE_RESTORE_BACKUP_DIR}_{timestamp}"
        print(f"\nMembuat backup konfigurasi saat ini ke: {pre_restore_path}")
        if os.path.exists(DESTINATION_DIR):
            os.rename(DESTINATION_DIR, pre_restore_path)

        # 2. Ekstrak file backup
        print(f"Mengekstrak {os.path.basename(latest_backup_file)} ke {DESTINATION_DIR}...")
        os.makedirs(DESTINATION_DIR, exist_ok=True)
        with zipfile.ZipFile(latest_backup_file, 'r') as zip_ref:
            zip_ref.extractall(DESTINATION_DIR)
            
        # 3. Hapus file backup yang sudah direstore
        os.remove(latest_backup_file)
        print(f"File backup '{os.path.basename(latest_backup_file)}' telah dihapus setelah restore.")

        print(f"\n{Colors.GREEN}{Colors.BOLD}Restore Selesai!{Colors.END}")
        print("Silakan restart layanan yang relevan (misal: 'systemctl restart xray').")

    except Exception as e:
        print(f"\n{Colors.RED}Terjadi error saat proses restore: {e}{Colors.END}")
        # Coba kembalikan backup sebelum restore jika terjadi error
        if 'pre_restore_path' in locals() and os.path.exists(pre_restore_path):
            if os.path.exists(DESTINATION_DIR):
                os.rmdir(DESTINATION_DIR) # Hapus direktori kosong yang mungkin dibuat
            os.rename(pre_restore_path, DESTINATION_DIR)
            print("Konfigurasi sebelum restore telah dikembalikan.")
        sys.exit(1)

if __name__ == "__main__":
    main()
