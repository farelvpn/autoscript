# Dokumentasi Web API AutoScript
### Dokumentasi ini merinci cara berinteraksi dengan Web API AutoScript untuk mengelola pengguna Vmess, Vless, dan Trojan secara terprogram.
---

## Informasi Dasar

- **Base URL (HTTPS):** `https://domain-anda.com/api/`
- **Base URL (HTTP):** `http://domain-anda.com:9000/`

Server API internal berjalan pada port **9000**. Nginx dikonfigurasi untuk me-proxy permintaan dari `https://domain-anda.com/api/` ke `http://127.0.0.1:9000/`.

---

## Autentikasi

Semua endpoint API diamankan menggunakan autentikasi **Bearer Token**. Anda harus menyertakan token yang valid di header `Authorization` pada setiap permintaan.

- **Header:** `Authorization: Bearer <TOKEN_ANDA>`

Token dapat dibuat atau dikelola menggunakan skrip `menu-api` di server, atau dengan mengedit file `/etc/api/key` secara manual.

### Contoh Permintaan (cURL)

```bash
curl -X POST 'https://domain-anda.com/api/add-trojan' \
-H 'Authorization: Bearer rerechan_xxxxxxxxxxxxxxx' \
-H 'Content-Type: application/json' \
-d '{"username": "user_baru", "quota": 10}'
```

Respons Kesalahan Umum
- 401 Unauthorized: Token otorisasi tidak valid atau tidak ada.
    
```JSON
{
    "message": "Unauthorized: Missing or invalid Bearer token"
}
```

- 400 Bad Request: Data JSON yang dikirim salah, tidak lengkap, atau tidak valid.
```JSON
{
    "status": "false",
    "code": 400,
    "message": "Input JSON tidak valid. 'username' dan 'quota' wajib diisi."
}
```

- 404 Not Found: Endpoint tidak ditemukan atau pengguna yang ditentukan tidak ada.
```JSON
{
    "status": "false",
    "code": 404,
    "message": "User 'nama_user' tidak ditemukan."
}
```

- 409 Conflict: Sumber daya yang ingin Anda buat (misalnya, pengguna) sudah ada.
```JSON

{
    "status": "false",
    "code": 409,
    "message": "Username ini sudah ada."
}
```

- 500 Internal Server Error: Terjadi kesalahan pada server saat mengeksekusi skrip.
```JSON
    {
        "error": "Script execution failed",
        "details": "...",
        "stderr": "..."
    }
```

---
# Endpoint Trojan
1. Buat Akun Trojan
- Endpoint: POST `/api/add-trojan`
- Deskripsi: Membuat akun Trojan baru.

## Request Body (JSON):
```JSON
{
    "username": "user_trojan_1",
    "quota": 10,
    "uuid": "opsional-uuid-kustom"
}
```

- quota: Dalam GB. Setel ke 0 untuk kuota tidak terbatas.
- uuid: Opsional. Jika tidak disediakan, UUID akan dibuat secara otomatis.

### Respons Sukses (201 Created):
```JSON
    {
        "status": "true",
        "code": 201,
        "message": "Akun Trojan berhasil dibuat",
        "data": {
            "username": "user_trojan_1",
            "uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "domain": "domain-anda.com",
            "limits": {
                "quota_gb": 10,
                "quota_display": "10 GB",
                "quota_bytes": 10737418240
            },
            "ports": {
                "trojan_ws_tls": 443,
                "trojan_ws_http": 80
            },
            "links": {
                "trojan_ws_tls": "trojan://...#user_trojan_1"
            }
        }
    }
```

2. Hapus Akun Trojan
- Endpoint: POST /api/delete-trojan
- Deskripsi: Menghapus akun Trojan secara permanen.

## Request Body (JSON):
```JSON
{
    "username": "user_trojan_1"
}
```

### Respons Sukses (200 OK):
```JSON

    {
        "status": "true",
        "code": 200,
        "message": "Akun 'user_trojan_1' berhasil dihapus permanen",
        "data": {
            "username": "user_trojan_1",
            "uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "files_removed": ["database", "quota_limit"]
        }
    }
```

3. Cek Akun Trojan
- Endpoint: POST /api/cek-trojan
- Deskripsi: Memeriksa detail, status kuota, dan info login akun Trojan.
## Request Body (JSON):
```JSON
{
    "username": "user_trojan_1"
}
```

### Respons Sukses (200 OK):
```JSON
    {
        "status": "true",
        "code": 200,
        "message": "Detail untuk user 'user_trojan_1' berhasil diambil",
        "data": {
            "username": "user_trojan_1",
            "uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "quota": {
                "limit_bytes": 10737418240,
                "limit_display": "10.00 GB",
                "usage_bytes": 536870912,
                "usage_display": "512.00 MB"
            },
            "login_info": {
                "total_ip_login": 2,
                "last_login": "2025/10/30 14:30:01",
                "active_ips": ["1.2.3.4", "5.6.7.8"]
            }
        }
    }
```

4. Tambah Kuota Trojan
- Endpoint: POST /api/add-quota-trojan
- Deskripsi: Menambahkan kuota ke total kuota akun Trojan yang sudah ada.
## Request Body (JSON):
```JSON
{
    "username": "user_trojan_1",
    "add_quota": 5
}
```
## add_quota: Jumlah kuota dalam GB yang akan ditambahkan.

### Respons Sukses (200 OK):
```JSON
    {
        "status": "true",
        "code": 200,
        "message": "Kuota untuk user 'user_trojan_1' berhasil ditambahkan",
        "data": {
            "username": "user_trojan_1",
            "quota_added": {
                "gb": 5,
                "bytes": 5368709120
            },
            "previous_total_quota": {
                "gb_display": "10.00 GB",
                "bytes": 10737418240
            },
            "new_total_quota": {
                "gb_display": "15.00 GB",
                "bytes": 16106127360
            },
            "telegram_notification": "sent"
        }
    }
```

# Endpoint Vmess
1. Buat Akun Vmess
- Endpoint: POST /api/add-vmess
- Deskripsi: Membuat akun Vmess baru.
## Request Body (JSON):
```JSON
{
    "username": "user_vmess_1",
    "quota": 10,
    "uuid": "opsional-uuid-kustom"
}
```

### Respons Sukses (201 Created):
```JSON
    {
        "status": "true",
        "code": 201,
        "message": "Akun VMESS berhasil dibuat",
        "data": {
            "username": "user_vmess_1",
            "uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "domain": "domain-anda.com",
            "limits": {
                "quota": 10,
                "quota_display": "10 GB",
                "quota_bytes": 10737418240
            },
            "ports": {
                "vmess_ws_tls": 443,
                "vmess_ws_http": 80
            },
            "links": {
                "vmess_ws_tls": "vmess://...",
                "vmess_ws_http": "vmess://..."
            }
        }
    }
```

2. Hapus Akun Vmess
- Endpoint: POST /api/delete-vmess
- Deskripsi: Menghapus akun Vmess secara permanen.

## Request Body (JSON):
```JSON
{
    "username": "user_vmess_1"
}
```

### Respons Sukses (200 OK):
```JSON
    {
        "status": "true",
        "code": 200,
        "message": "Akun 'user_vmess_1' berhasil dihapus permanen",
        "data": {
            "username": "user_vmess_1",
            "uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "files_removed": ["database", "quota_limit"]
        }
    }
```

3. Cek Akun Vmess
- Endpoint: POST /api/cek-vmess
- Deskripsi: Memeriksa detail, status kuota, dan info login akun Vmess.

## Request Body (JSON):
```JSON
{
    "username": "user_vmess_1"
}
```

### Respons Sukses (200 OK):
```JSON
    {
        "status": "true",
        "code": 200,
        "message": "Detail untuk user 'user_vmess_1' berhasil diambil",
        "data": {
            "username": "user_vmess_1",
            "uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "quota": {
                "limit_bytes": 10737418240,
                "limit_display": "10.00 GB",
                "usage_bytes": 2147483648,
                "usage_display": "2.00 GB"
            },
            "login_info": {
                "total_ip_login": 1,
                "last_login": "2025/10/30 15:00:00",
                "active_ips": ["10.20.30.40"]
            }
        }
    }
```

4. Tambah Kuota Vmess
- Endpoint: POST /api/add-quota-vmess
- Deskripsi: Menambahkan kuota ke total kuota akun Vmess yang sudah ada.

## Request Body (JSON):
```JSON
{
    "username": "user_vmess_1",
    "add_quota": 5
}
```

### Respons Sukses (200 OK):
```JSON

    {
        "status": "true",
        "code": 200,
        "message": "Kuota untuk user VMess 'user_vmess_1' berhasil ditambahkan",
        "data": {
            "username": "user_vmess_1",
            "quota_added": {
                "gb": 5,
                "bytes": 5368709120
            },
            "previous_total_quota": {
                "gb_display": "10.00 GB",
                "bytes": 10737418240
            },
            "new_total_quota": {
                "gb_display": "15.00 GB",
                "bytes": 16106127360
            },
            "telegram_notification": "sent"
        }
    }
```

# Endpoint Vless

1. Buat Akun Vless
- Endpoint: POST /api/add-vless
- Deskripsi: Membuat akun Vless baru.

## Request Body (JSON):
```JSON
{
    "username": "user_vless_1",
    "quota": 10,
    "uuid": "opsional-uuid-kustom"
}
```

### Respons Sukses (201 Created):
```JSON
    {
        "status": "true",
        "code": 201,
        "message": "Akun VLESS berhasil dibuat",
        "data": {
            "username": "user_vless_1",
            "uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "domain": "domain-anda.com",
            "limits": {
                "quota": 10,
                "quota_display": "10 GB",
                "quota_bytes": 10737418240
            },
            "ports": {
                "vless_ws_tls": 443,
                "vless_ws_http": 80
            },
            "links": {
                "vless_ws_tls": "vless://...",
                "vless_ws_http": "vless://..."
            }
        }
    }
```

2. Hapus Akun Vless
- Endpoint: POST /api/delete-vless
- Deskripsi: Menghapus akun Vless secara permanen.

## Request Body (JSON):
```JSON
{
    "username": "user_vless_1"
}
```

### Respons Sukses (200 OK):
```JSON
    {
        "status": "true",
        "code": 200,
        "message": "Akun VLESS 'user_vless_1' berhasil dihapus permanen",
        "data": {
            "username": "user_vless_1",
            "uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "files_removed": ["database", "quota_limit"]
        }
    }
```

3. Cek Akun Vless
- Endpoint: POST /api/cek-vless
- Deskripsi: Memeriksa detail, status kuota, dan info login akun Vless.

## Request Body (JSON):
```JSON
{
    "username": "user_vless_1"
}
```

### Respons Sukses (200 OK):
```JSON
    {
        "status": "true",
        "code": 200,
        "message": "Detail untuk user VLESS 'user_vless_1' berhasil diambil",
        "data": {
            "username": "user_vless_1",
            "uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "quota": {
                "limit_bytes": 10737418240,
                "limit_display": "10.00 GB",
                "usage_bytes": 1073741824,
                "usage_display": "1.00 GB"
            },
            "login_info": {
                "total_ip_login": 1,
                "last_login": "2025/10/30 12:10:15",
                "active_ips": ["192.168.1.10"]
            }
        }
    }
```

4. Tambah Kuota Vless
- Endpoint: POST /api/add-quota-vless
- Deskripsi: Menambahkan kuota ke total kuota akun Vless yang sudah ada.

## Request Body (JSON):
```JSON
{
    "username": "user_vless_1",
    "add_quota": 5
}
```

### Respons Sukses (200 OK):
```JSON
    {
        "status": "true",
        "code": 200,
        "message": "Kuota untuk user VLESS 'user_vless_1' berhasil ditambahkan",
        "data": {
            "username": "user_vless_1",
            "quota_added": {
                "gb": 5,
                "bytes": 5368709120
            },
            "previous_total_quota": {
                "gb_display": "10.00 GB",
                "bytes": 10737418240
            },
            "new_total_quota": {
                "gb_display": "15.00 GB",
                "bytes": 16106127360
            },
            "telegram_notification": "sent"
        }
    }
```
