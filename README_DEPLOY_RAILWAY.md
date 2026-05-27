# Deploy Pathora ke Railway

Panduan ini menyiapkan deploy Flask + SQLite + persistent upload storage di Railway. Jangan commit file `.env` dan jangan menaruh API key asli di repository.

## 1. Push project ke GitHub

Jalankan dari root project Flask, yaitu folder yang berisi `app.py`, `requirements.txt`, dan `Procfile`.

```powershell
git status
git add .
git commit -m "Prepare Railway deployment"
git push
```

## 2. Import project di Railway

1. Buka Railway dashboard.
2. Pilih **New Project**.
3. Pilih **Deploy from GitHub repo**.
4. Pilih repository Pathora.
5. Pastikan Railway membaca root project yang berisi `Procfile`.

## 3. Start command

Gunakan start command berikut:

```text
gunicorn app:app
```

`Procfile` di project juga sudah berisi:

```text
web: python tools/build_frontend_assets.py && gunicorn app:app
```

Perintah ini membuat asset production di `static/dist/` sebelum server Flask
dijalankan. Aktifkan built asset dengan variable:

```text
USE_BUILT_ASSETS=true
```

## 4. Environment variables Railway

Isi variable berikut di Railway dashboard, bukan di repository:

```text
DATA_DIR=/app/data
SECRET_KEY=<random panjang>
ADMIN_PASSWORD=<password admin kuat>
GOOGLE_API_KEY=<isi di Railway dashboard, jangan commit>
GOOGLE_MODEL=gemma-4-26b-a4b-it
GOOGLE_TIMEOUT_SECONDS=120
USE_BUILT_ASSETS=true
```

Catatan:
- `SECRET_KEY` harus string random panjang untuk session Flask.
- `ADMIN_PASSWORD` wajib di production; jangan gunakan password demo.
- `GOOGLE_API_KEY` hanya disimpan di Railway Variables.
- Jika model Google yang dipakai project berubah, sesuaikan `GOOGLE_MODEL`.

## 5. Persistent volume

Tambahkan volume di service Railway:

```text
Mount path: /app/data
Size: 1GB atau sesuai plan
```

Dengan `DATA_DIR=/app/data`, Pathora menyimpan data production di:

```text
/app/data/app.db
/app/data/uploads/documents/
/app/data/uploads/avatars/
/app/data/uploads/chat/
```

Tanpa volume, file SQLite dan upload dapat hilang saat redeploy atau restart container.

## 6. Public domain

1. Buka service Pathora di Railway.
2. Masuk ke tab **Settings**.
3. Cari bagian **Networking**.
4. Klik **Generate Domain**.
5. Buka domain public yang dibuat Railway.

## 7. Test setelah deploy

Cek halaman dan workflow berikut:

```text
/
/register
/login
/dashboard
/opportunities
/documents
/chat
/help?context=chat
```

Lakukan smoke test:
- Register user baru.
- Login.
- Buka Pusat Bantuan sebagai jobseeker dan pastikan kategori Recruiter/Admin tidak muncul.
- Buka Pusat Bantuan sebagai recruiter dan pastikan kategori Admin tidak muncul.
- Upload avatar atau dokumen kecil.
- Kirim chat dengan gambar kecil jika fitur chat dipakai.
- Restart/redeploy service Railway.
- Pastikan database, upload dokumen, avatar, dan attachment chat tetap ada.

## 8. Troubleshooting singkat

- Jika aplikasi gagal start, cek Railway logs dan pastikan `SECRET_KEY` sudah diisi.
- Jika database kosong setelah redeploy, pastikan volume sudah mounted ke `/app/data`.
- Jika upload hilang setelah redeploy, pastikan `DATA_DIR=/app/data` dan volume aktif.
- Jika AI Assistant tidak aktif, pastikan `GOOGLE_API_KEY` valid di Railway Variables.
