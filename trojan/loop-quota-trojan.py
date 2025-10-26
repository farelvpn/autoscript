#!/usr/bin/env python3
import subprocess
import time
import sys

# Nama perintah yang akan dijalankan.
COMMAND = "quota-trojan"

# Interval jeda antar eksekusi dalam detik.
INTERVAL = 2

try:
    print(f"Memulai perulangan: menjalankan '{COMMAND}' setiap {INTERVAL} detik.")
    print("Tekan Ctrl+C untuk berhenti.")
    
    # Perulangan tanpa henti (setara dengan 'for (( ; ; ))' di Bash).
    while True:
        try:
            # Menjalankan perintah eksternal.
            # 'check=True' akan menampilkan error jika perintah gagal.
            subprocess.run([COMMAND], check=True)
            
        except FileNotFoundError:
            # Error jika perintah 'quota-trojan' tidak ditemukan.
            print(f"Error: Perintah '{COMMAND}' tidak ditemukan. Pastikan file tersebut ada dan executable.", file=sys.stderr)
            sys.exit(1) # Keluar dari script jika perintah tidak ada.
            
        except subprocess.CalledProcessError as e:
            # Error jika 'quota-trojan' keluar dengan status error.
            print(f"Error saat menjalankan '{COMMAND}': {e}", file=sys.stderr)

        # Jeda selama interval yang ditentukan.
        time.sleep(INTERVAL)

except KeyboardInterrupt:
    # Menangani jika pengguna menekan Ctrl+C untuk keluar.
    print("\nPerulangan dihentikan oleh pengguna.")
    sys.exit(0)
