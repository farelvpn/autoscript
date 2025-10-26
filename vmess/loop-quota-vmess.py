#!/usr/bin/env python3
import subprocess
import time
import sys

# Nama perintah yang akan dijalankan.
COMMAND = "quota-vmess"

# Interval jeda antar eksekusi dalam detik.
INTERVAL = 2

try:
    print(f"Memulai perulangan: menjalankan '{COMMAND}' setiap {INTERVAL} detik.")
    print("Tekan Ctrl+C untuk berhenti.")
    
    while True:
        try:
            subprocess.run([COMMAND], check=True)
        except FileNotFoundError:
            print(f"Error: Perintah '{COMMAND}' tidak ditemukan.", file=sys.stderr)
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            print(f"Error saat menjalankan '{COMMAND}': {e}", file=sys.stderr)

        time.sleep(INTERVAL)

except KeyboardInterrupt:
    print("\nPerulangan dihentikan oleh pengguna.")
    sys.exit(0)
