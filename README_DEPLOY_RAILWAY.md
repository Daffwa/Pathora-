# Deploy Pathora ke Railway

Panduan ini menyiapkan deploy Flask + SQLAlchemy + database server di Railway. Jangan commit file `.env` dan jangan menaruh API key asli di repository.

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
APP_ENV=production
DATA_DIR=/app/data
DATABASE_URL=<PostgreSQL/MySQL database URL dari Railway>
SECRET_KEY=<random panjang>
PASSWORD_RESET_SECRET=<random panjang berbeda dari SECRET_KEY>
ADMIN_PASSWORD=<password admin kuat>
PUBLIC_BASE_URL=<https://domain Railway/custom domain>
TRUSTED_HOSTS=<domain Railway/custom domain>
GOOGLE_API_KEY=<isi di Railway dashboard, jangan commit>
GOOGLE_MODEL=gemma-4-26b-a4b-it
GOOGLE_TIMEOUT_SECONDS=120
USE_BUILT_ASSETS=true
RATE_LIMIT_BACKEND=database
MAIL_SERVER=<smtp.example.com>
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=<akun SMTP>
MAIL_PASSWORD=<password SMTP>
MAIL_DEFAULT_SENDER=Pathora <no-reply@example.com>
```

Catatan:
- `APP_ENV=production` mengaktifkan validasi konfigurasi fail-closed.
- `SECRET_KEY` harus string random panjang untuk session Flask.
- `PASSWORD_RESET_SECRET` harus random dan berbeda dari `SECRET_KEY`.
- `ADMIN_PASSWORD` wajib di production; jangan gunakan password demo.
- `DATABASE_URL` mengarah ke service PostgreSQL/MySQL Railway dan wajib di production.
- `PUBLIC_BASE_URL` dipakai untuk link reset password agar tidak mempercayai Host header request. Jika variable ini tidak terbaca di Railway, aplikasi dapat fallback ke `https://$RAILWAY_PUBLIC_DOMAIN` yang disediakan otomatis oleh Railway.
- `TRUSTED_HOSTS` berisi hostname production yang boleh diterima aplikasi.
- `RATE_LIMIT_BACKEND=database` memakai database sebagai penyimpanan rate limit antar worker/restart.
- `MAIL_*` dipakai untuk mengirim email reset password. Tanpa konfigurasi SMTP lengkap, request lupa password tetap netral tetapi email reset tidak dikirim.
- `GOOGLE_API_KEY` hanya disimpan di Railway Variables.
- Jika model Google yang dipakai project berubah, sesuaikan `GOOGLE_MODEL`.

## Using Supabase PostgreSQL

Railway tetap menjalankan aplikasi Flask, sedangkan database production bisa memakai Supabase PostgreSQL melalui `DATABASE_URL`.

1. Di Supabase Dashboard, buka project lalu klik **Connect**.
2. Salin connection string Postgres. Untuk service Flask/Gunicorn yang persistent, pilih direct connection jika jaringan Railway mendukung endpoint tersebut, atau session pooler jika butuh IPv4. Hindari transaction pooler untuk migration kecuali sudah diuji.
3. Paste string tersebut ke Railway Variables sebagai `DATABASE_URL`, contoh:

```text
DATABASE_URL=postgresql://postgres.project_ref:<password>@aws-region.pooler.supabase.com:5432/postgres?sslmode=require
```

Pastikan variable berikut juga ada di Railway: `APP_ENV=production`, `SECRET_KEY`, `PASSWORD_RESET_SECRET`, `ADMIN_PASSWORD`, `PUBLIC_BASE_URL` atau domain otomatis `RAILWAY_PUBLIC_DOMAIN`, `TRUSTED_HOSTS`, `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER`, dan `RATE_LIMIT_BACKEND=database`.

Yang tidak berubah:
- Aplikasi tetap memakai Flask session auth, bukan Supabase Auth.
- Upload tetap memakai folder/volume aplikasi, bukan Supabase Storage.
- SQLAlchemy ORM dan Alembic migrations tetap menjadi jalur schema/database.

Catatan keamanan:
- Jangan taruh Supabase `service_role` key, secret key, database password, atau connection string di frontend, file `.env` yang dicommit, template publik, atau JavaScript.
- Karena Pathora mengakses database dari server melalui SQLAlchemy, tabel tidak perlu diekspos ke Supabase Data API. Jangan buka akses Data API ke tabel public kecuali RLS dan policy sudah dirancang, diuji, dan memang dibutuhkan.
- Jalankan migration dan smoke test pada database/branch test sebelum mengarah ke production.
- Jika Supabase project tersedia, jalankan Security Advisor dan Performance Advisor setelah schema terpasang. Jika hanya memakai dashboard, buka **Database** / **Advisors** di Supabase dan review temuan secara manual.

## 5. Persistent upload storage

Database production sebaiknya memakai service PostgreSQL/MySQL melalui `DATABASE_URL`.
Volume tetap diperlukan untuk file upload jika penyimpanan belum dipindahkan ke object storage.

Tambahkan volume di service Railway:

```text
Mount path: /app/data
Size: 1GB atau sesuai plan
```

Dengan `DATA_DIR=/app/data`, Pathora menyimpan file upload di:

```text
/app/data/uploads/documents/
/app/data/uploads/avatars/
/app/data/uploads/chat/
```

Tanpa volume, file upload dapat hilang saat redeploy atau restart container.

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
- Jika database tidak terhubung, pastikan `DATABASE_URL` benar dan service database aktif.
- Jika upload hilang setelah redeploy, pastikan `DATA_DIR=/app/data` dan volume aktif.
- Jika AI Assistant tidak aktif, pastikan `GOOGLE_API_KEY` valid di Railway Variables.
