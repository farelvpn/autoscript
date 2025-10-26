#!/usr/bin/env python3
# ========================================================
# Script Name: user-info (Python Version)
# Description: API script to get detailed login and usage info for a specific Trojan user.
# Executed by: Python WebAPI Server
# ========================================================

import sys
import json
import os
import re

# --- Konfigurasi Path & Konstanta ---
PATH_CONFIG = '/etc/xray/config.json'
PATH_LOG = '/var/log/xray/access.log'
DIR_DATABASE = '/etc/xray/database/trojan'
DIR_QUOTA = '/etc/xray/limit/quota/trojan'
DIR_USAGE = '/etc/xray/usage/quota/trojan'

# --- Fungsi Bantuan (Helpers) ---

def print_json_response(data, success=True, code=200):
    """Mencetak output dalam format JSON standar."""
    response = {
        "status": str(success).lower(),
        "code": code,
    }
    if success:
        response["message"] = f"Detail untuk user '{data.get('username')}' berhasil diambil"
        response["data"] = data
    else:
        response["message"] = data.get("message", "Terjadi kesalahan")
    
    print(json.dumps(response, indent=4))
    sys.exit(0 if success else 1)

def parse_db_file(file_path):
    """Membaca file database user untuk mendapatkan UUID."""
    try:
        with open(file_path, 'r') as f:
            for line in f:
                if line.startswith("uuid:"):
                    return line.split(":", 1)[1].strip()
    except FileNotFoundError:
        return None
    return None

def bytes_to_human(byte_count):
    """Mengonversi byte menjadi format yang mudah dibaca (KB, MB, GB)."""
    if byte_count is None or byte_count == 0:
        return "0 B"
    power = 1024
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while byte_count >= power and n < len(power_labels):
        byte_count /= power
        n += 1
    return f"{byte_count:.2f} {power_labels[n]}B"

def get_quota_info(username):
    """Mendapatkan informasi kuota dan penggunaan."""
    limit_path = os.path.join(DIR_QUOTA, username)
    usage_path = os.path.join(DIR_USAGE, username)
    
    quota_limit_bytes = 0
    try:
        with open(limit_path, 'r') as f:
            quota_limit_bytes = int(f.read().strip())
    except (FileNotFoundError, ValueError):
        pass # Jika file tidak ada atau kosong, limit dianggap 0

    quota_usage_bytes = 0
    try:
        with open(usage_path, 'r') as f:
            quota_usage_bytes = int(f.read().strip())
    except (FileNotFoundError, ValueError):
        pass

    return {
        "limit_bytes": quota_limit_bytes,
        "limit_display": "Unlimited" if quota_limit_bytes == 0 else bytes_to_human(quota_limit_bytes),
        "usage_bytes": quota_usage_bytes,
        "usage_display": bytes_to_human(quota_usage_bytes)
    }

def parse_access_log(username):
    """Mem-parsing log akses Xray untuk mendapatkan info login."""
    active_ips = set()
    last_login = "N/A"
    
    try:
        # Menggunakan regex untuk mencocokkan baris log dengan lebih andal
        log_pattern = re.compile(
            r"(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}).*? "
            r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):\d+ accepted.*?"
            f"email: {username}"
        )
        
        with open(PATH_LOG, 'r') as f:
            for line in f:
                match = log_pattern.search(line)
                if match:
                    last_login = match.group(1) # Timestamp akan selalu ter-update ke yang terakhir
                    active_ips.add(match.group(2)) # IP address
                    
    except FileNotFoundError:
        return {"total_ip_login": 0, "last_login": "Log file not found", "active_ips": []}

    return {
        "total_ip_login": len(active_ips),
        "last_login": last_login,
        "active_ips": sorted(list(active_ips))
    }


# --- Logika Utama ---

def get_user_info(params):
    """Fungsi utama untuk mendapatkan detail user."""
    username = params.get("username")

    # 1. Validasi Input
    if not username:
        print_json_response({"message": "Input JSON tidak valid. 'username' wajib diisi."}, success=False, code=400)
    
    db_path = os.path.join(DIR_DATABASE, f"{username}.txt")
    if not os.path.exists(db_path):
        print_json_response({"message": f"User '{username}' tidak ditemukan."}, success=False, code=404)

    # 2. Kumpulkan Semua Data
    user_uuid = parse_db_file(db_path)
    quota_info = get_quota_info(username)
    login_info = parse_access_log(username)

    # 3. Susun Respons JSON
    response_data = {
        "username": username,
        "uuid": user_uuid,
        "quota": quota_info,
        "login_info": login_info
    }
    
    print_json_response(response_data, success=True, code=200)

if __name__ == "__main__":
    try:
        input_json = sys.stdin.read()
        params = json.loads(input_json)
        get_user_info(params)
    except json.JSONDecodeError:
        print_json_response({"message": "Gagal mem-parsing input. Pastikan format JSON sudah benar."}, success=False, code=400)
    except Exception as e:
        print_json_response({"message": f"Terjadi kesalahan internal: {str(e)}"}, success=False, code=500)
