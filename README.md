# AutoScript

Selamat datang di AutoScript. Proyek ini adalah kumpulan skrip otomatisasi yang dirancang untuk menyederhanakan instalasi, konfigurasi, dan pengelolaan layanan Xray (termasuk Vmess, Vless, dan Trojan) di server Linux.
Dilengkapi dengan Web API untuk manajemen terprogram, sistem pemantauan kuota otomatis, dan notifikasi Telegram, proyek ini bertujuan untuk menyediakan solusi manajemen server Xray yang tangguh dan mudah digunakan.
Proyek ini bersifat open-source. Kami menyambut baik kontribusi, fork, dan pull request dari komunitas.


## Fitur
- Instalasi Otomatis: Skrip instalasi tunggal untuk menyiapkan Xray, Nginx, sertifikat SSL (via Certbot), dan semua dependensi yang diperlukan.
- Manajemen Pengguna: Fungsionalitas untuk menambah, menghapus, dan memantau pengguna untuk layanan Vmess, Vless, dan Trojan.
- Manajemen Kuota: Secara otomatis memantau penggunaan data pengguna dan menonaktifkan akun yang telah melampaui kuota yang ditentukan.
- Web API: Menyediakan antarmuka API RESTful yang aman (menggunakan otorisasi Bearer Token) untuk mengelola pengguna dan kuota dari jarak jauh.
- Notifikasi Telegram: Mengirimkan notifikasi otomatis ke obrolan Telegram yang Anda tentukan saat akun dibuat, dihapus, atau kuota habis.
- Menu Interaktif: Skrip menu berbasis terminal yang mudah digunakan untuk mengelola domain, sertifikat SSL, kredensial API, dan pengaturan Telegram.
- Pencadangan & Pemulihan: Skrip bawaan untuk mencadangkan dan memulihkan direktori konfigurasi Xray Anda.

# Instalasi
Untuk melakukan instalasi penuh dari AutoScript Xray Panel, cukup jalankan perintah berikut sebagai pengguna root di server Anda:
```
apt update ; apt install wget curl binutils openssl -y ; bash <(curl -Lks https://raw.githubusercontent.com/farelvpn/autoscript/refs/heads/main/install.sh)
```


Skrip instalasi akan memandu Anda melalui langkah-langkah berikut:
1. Memperbarui sistem dan menginstal paket yang diperlukan (seperti curl, nginx, python3, certbot).
2. Meminta Anda untuk memasukkan nama domain untuk server Anda.
3. Menginstal Xray-core dan Nginx.
4. Secara otomatis mendapatkan sertifikat SSL/TLS untuk domain Anda menggunakan Certbot.
5. Mengkonfigurasi Xray dan Nginx untuk bekerja bersama sebagai reverse proxy.
6. Menyalin semua skrip manajemen (API, kuota, menu) ke direktori yang sesuai (seperti /usr/local/sbin/ dan /usr/local/sbin/api/).
7. Menyiapkan dan memulai layanan systemd untuk menjalankan Web API dan skrip pemantauan kuota secara terus-menerus.


### Struktur Proyek
- `/etc/xray/`: Direktori konfigurasi utama.
  - `config.json`: File konfigurasi inti Xray.
  - `domain`: Menyimpan nama domain server Anda saat ini.
  - `bot.key, client.id`: Menyimpan kredensial untuk notifikasi Telegram.
- `database/`: Menyimpan file database sederhana untuk setiap pengguna.
  - `limit/quota/`: Menyimpan batas kuota untuk setiap pengguna.
  - `usage/quota/`: Menyimpan penggunaan kuota saat ini untuk setiap pengguna.
- `/etc/api/key`: Menyimpan token Bearer yang valid untuk mengakses Web API.
- `/usr/local/sbin/api/`: Berisi skrip Python yang dieksekusi oleh Web API (misalnya, add-trojan, delete-vmess).
- `/usr/local/sbin/`: Berisi skrip utilitas dan menu (misalnya, menu-api, quota-trojan, backup).
- `/etc/systemd/system/`: Berisi file layanan systemd (misalnya, server.service, quota-trojan.service).


### Manajemen Server (Menu Terminal)

Anda dapat dengan mudah mengelola server Anda menggunakan skrip menu interaktif:

- Mengelola Domain & SSL:
```shell
menu-domain
```
### Gunakan menu ini untuk mengubah nama domain server Anda atau memperbarui sertifikat SSL Anda secara manual.
- Mengelola Web API:
```shell
menu-api
```
### Gunakan menu ini untuk membuat token API baru, mengedit file token, atau me-restart layanan API.

- Mengelola Notifikasi Telegram:
```shell
telegram-info
```
### Gunakan menu ini untuk menambah, mengubah, atau memvalidasi Bot Token dan Chat ID Telegram Anda.

Mengubah Versi Xray:
```shell
versi-xray
```
### Gunakan menu ini untuk beralih di antara berbagai versi Xray-core yang tersedia.

## Pencadangan & Pemulihan
Proyek ini dilengkapi dengan skrip sederhana untuk pencadangan dan pemulihan.
- Membuat Cadangan: Skrip `backup` secara otomatis membuat arsip `.zip` dari direktori `/etc/xray` Anda dan mengirimkannya ke obrolan Telegram Anda. Ini diatur untuk berjalan secara otomatis melalui crontab.

Memulihkan Cadangan:
1. Unduh file `backup-YYYY-MM-DD_HH-MM-SS.zip` terbaru dari obrolan Telegram Anda dan unggah ke direktori `/root` di server Anda.
2. Jalankan perintah berikut:
```shell
restore
```
### Skrip akan secara otomatis menemukan file cadangan terbaru di /root, mencadangkan konfigurasi Anda saat ini (sebagai tindakan pengamanan), dan memulihkan data dari file .zip.

## Berkontribusi:
### Kami sangat menyambut kontribusi dari komunitas untuk membuat proyek ini lebih baik. Jika Anda ingin berkontribusi, silakan ikuti panduan berikut:
1. Fork repositori ini ke akun GitHub Anda.
2. Buat cabang baru (`git checkout -b fitur/nama-fitur-baru`.
3. Lakukan perubahan Anda dan commit dengan pesan yang jelas (`git commit -m 'Menambahkan fitur X'`).
4. Push perubahan Anda ke repositori fork Anda (`git push origin fitur/nama-fitur-baru`).
5. Buka Pull Request ke repositori asli.

## Lisensi:
Proyek ini dilisensikan di bawah Lisensi [MIT](LICENSE).
