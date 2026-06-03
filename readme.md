# Pathora — Smart Internship & Scholarship Tracker

Aplikasi web Flask untuk membantu mahasiswa menemukan peluang magang/beasiswa, melacak lamaran, mengelola dokumen, dan mendapatkan rekomendasi berbasis skor prioritas. Juga menyediakan dashboard rekruter untuk mengelola pelamar.

## Teknologi

- Python 3.12
- Flask 3.0
- SQLAlchemy ORM + Flask-Migrate
- SQLite untuk fallback lokal, PostgreSQL/MySQL via `DATABASE_URL`
- Google Gemini API (AI Assistant)
- Gunicorn (deploy production)
- HTML, CSS, JavaScript
- Jinja Template

## Cara Menjalankan Lokal

```powershell
python -m pip install -r requirements.txt
$env:APP_ENV="development"
python app.py
```

Buka:

```text
http://127.0.0.1:5000
```

Database, migration Alembic, dan folder upload akan disiapkan otomatis saat pertama kali dijalankan. Jika `DATABASE_URL` tidak diisi, aplikasi memakai SQLite lokal sebagai fallback development.

## Build Asset Frontend

Untuk production, gabungkan dan compact CSS/JS terlebih dahulu:

```powershell
python tools\build_frontend_assets.py
```

Script ini membuat file hasil build di `static/dist/`, source map `.map`, dan
manifest di `static/dist/asset-manifest.json`. Set `USE_BUILT_ASSETS=true` agar
template memakai file hasil build. Jika manifest belum ada, aplikasi otomatis
fallback ke file `static/css` dan `static/js` biasa.

Untuk cek kualitas frontend:

```powershell
python tools\lint_frontend_assets.py
```

Di Railway, `Procfile` sudah menjalankan build sebelum Gunicorn, jadi deploy
tidak bergantung pada file `static/dist/` lama.

## Akun Bawaan

| Role      | Email              | Password    |
|-----------|--------------------|-------------|
| Admin     | admin@example.com  | admin12345 |
| Student   | (register sendiri) |             |
| Recruiter | (register sendiri) |             |

Admin dibuat otomatis jika belum ada. Password `admin12345` hanya fallback untuk `APP_ENV=development` atau `APP_ENV=test`; production wajib mengisi `ADMIN_PASSWORD` yang kuat. Password disimpan dalam bentuk hash.

## Role dan Akses

### Student
- Register, login, logout
- Melihat, mencari, filter, sort peluang
- Menyimpan peluang (bookmark)
- Melacak status lamaran
- Upload/reset dokumen (CV, transkrip, portofolio)
- Dashboard personal dengan priority score
- Chat dengan recruiter
- AI Assistant untuk rekomendasi dan pertanyaan
- Pusat Bantuan yang menyembunyikan kategori Recruiter dan Admin

### Recruiter
- Dashboard rekruter dengan ringkasan pelamar
- Mengelola lowongan (CRUD)
- Melihat daftar pelamar per lowongan
- Mengubah status lamaran (Ditinjau/Diterima/Ditolak)
- Chat dengan pelamar
- Melihat profil dan dokumen pelamar
- Pusat Bantuan yang menyembunyikan kategori Admin

### Admin
- Semua akses recruiter
- Mengelola seluruh lowongan dari semua recruiter
- Melihat ringkasan jumlah internship/scholarship
- Menghapus lowongan dengan cascade
- Pusat Bantuan dengan kategori Admin dan Recruiter

## Fitur Utama

- Authentication dengan Flask session
- Role-based access control (decorator guards) dengan permission matrix
- Status akun recruiter untuk moderasi (`pending`, `approved`, `rejected`) dengan register default `approved`
- Audit log untuk aksi penting seperti login, upload dokumen, lowongan, dan status applicant
- CSRF protection untuk form dan request AJAX
- Security headers dan cookie hardening untuk production
- Rate limiting untuk login, AI Assistant, dan chat
- Opportunity discovery dengan filter dan sort
- Saved opportunities (bookmark)
- Application tracker
- Document tracker dengan upload lokal
- Smart priority score (deadline + skill match + dokumen)
- Dashboard ringkasan personal & recruiter
- Chat real-time antar pengguna
- AI Assistant (Gemini API)
- Pusat Bantuan role-aware untuk Student, Recruiter, dan Admin
- Frontend asset build dengan hash filename, source map, dan lint ringan
- Admin & Recruiter CRUD opportunities
- Error page 404, 403, 413
- Mobile responsive

## Konfigurasi Production Penting

Set environment variable berikut sebelum deploy:

```text
APP_ENV=production
SECRET_KEY=<random panjang>
PASSWORD_RESET_SECRET=<random panjang berbeda dari SECRET_KEY>
ADMIN_PASSWORD=<password admin yang kuat>
DATABASE_URL=<postgresql://... atau mysql+pymysql://...>
PUBLIC_BASE_URL=https://domain-produksi.example
TRUSTED_HOSTS=domain-produksi.example
DATA_DIR=/app/data
USE_BUILT_ASSETS=true
RATE_LIMIT_BACKEND=database
MAIL_SERVER=<smtp.example.com>
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=<akun SMTP>
MAIL_PASSWORD=<password SMTP>
MAIL_DEFAULT_SENDER=Pathora <no-reply@example.com>
GOOGLE_API_KEY=<isi lewat dashboard hosting>
```

Catatan:
- `APP_ENV` wajib jelas. Gunakan `development` atau `test` hanya untuk lokal/test; selain itu aplikasi mewajibkan konfigurasi production.
- `SECRET_KEY` dan `PASSWORD_RESET_SECRET` wajib di production untuk menjaga session dan token reset tetap aman.
- `ADMIN_PASSWORD` wajib di production; fallback `admin12345` hanya untuk development/test.
- `DATABASE_URL` wajib di production. Jika kosong, aplikasi hanya memakai SQLite lokal saat `APP_ENV=development` atau `APP_ENV=test`.
- `PUBLIC_BASE_URL` dipakai untuk membuat link reset password; `TRUSTED_HOSTS` membatasi Host header yang diterima.
- `RATE_LIMIT_BACKEND=database` membuat rate limit production tersimpan di database bersama, bukan memori proses.
- `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, dan `MAIL_DEFAULT_SENDER` wajib diisi jika fitur lupa password perlu mengirim email reset. `MAIL_USE_TLS=true` disarankan untuk SMTP port 587.
- Isi `TRUSTED_PROXY_IPS` hanya dengan IP/CIDR proxy yang dipercaya jika aplikasi perlu membaca `X-Forwarded-For`.
- `USE_BUILT_ASSETS=true` membuat template memakai file di `static/dist/`.
- Jika memakai Railway, `Procfile` sudah menjalankan build asset sebelum Gunicorn.

## Using Supabase PostgreSQL

Pathora dapat memakai Supabase PostgreSQL sebagai database production cukup dengan mengisi `DATABASE_URL`. Aplikasi tetap memakai Flask session auth, SQLAlchemy ORM, repository/service/controller MVC, dan Alembic migrations. Integrasi ini tidak memindahkan auth ke Supabase Auth dan tidak memindahkan upload ke Supabase Storage.

Langkah minimal:

1. Buat atau pilih project Supabase.
2. Di Supabase Dashboard, buka **Connect** dan salin connection string Postgres. Untuk backend Flask persistent, gunakan direct connection jika network mendukung IPv6/IPv4 add-on, atau session pooler jika runtime production hanya IPv4. Transaction pooler lebih cocok untuk serverless sementara dan dapat membatasi fitur prepared statement.
3. Simpan connection string tersebut sebagai `DATABASE_URL` di environment production, misalnya:

```text
DATABASE_URL=postgresql://postgres.project_ref:<password>@aws-region.pooler.supabase.com:5432/postgres?sslmode=require
```

Set juga variable production berikut: `APP_ENV=production`, `SECRET_KEY`, `PASSWORD_RESET_SECRET`, `ADMIN_PASSWORD`, `PUBLIC_BASE_URL`, `TRUSTED_HOSTS`, `MAIL_*`, dan `RATE_LIMIT_BACKEND=database`.

Catatan keamanan Supabase:
- Jangan expose Supabase `service_role` key, secret key, atau database password ke frontend, `static/`, template publik, log, atau file yang dicommit.
- Karena aplikasi ini mengakses database server-side melalui SQLAlchemy, tabel tidak perlu dibuka ke Supabase Data API untuk frontend. Jangan expose tabel lewat Data API kecuali RLS dan policy sudah sengaja didesain dan diuji.
- Jalankan Alembic migration ke Supabase dari environment backend yang memakai `DATABASE_URL` production/branch yang benar. Gunakan project/branch test dulu sebelum production.
- Supabase advisors tidak bisa dijalankan dari repo lokal tanpa akses project. Jika project tersedia, jalankan Security Advisor dan Performance Advisor setelah migration pada branch/test database, lalu perbaiki temuan sebelum production.

## Struktur Proyek

```text
app.py                          # Entry point + factory create_app()
config.py                       # Konfigurasi env, database URL, upload folder, dll
requirements.txt                # Dependencies Python

extensions.py                   # Inisialisasi SQLAlchemy dan Flask-Migrate

models/                         # SQLAlchemy ORM per domain
    user.py
    opportunity.py
    application.py
    document.py
    bookmark.py
    chat.py
    audit_log.py

dto/                            # Data transfer/view models non-ORM
    user.py
    opportunity.py
    document.py

repositories/                   # Query dan persistence SQLAlchemy
    user_repository.py
    opportunity_repository.py
    application_repository.py
    document_repository.py

migrations/                     # Alembic migration sebagai sumber schema database

controllers/                    # Route layer aktif yang diregister oleh app.py
    auth_controller.py
    public_controller.py
    dashboard_controller.py
    opportunity_controller.py
    application_controller.py
    document_controller.py
    profile_controller.py
    chat_controller.py
    recruiter_controller.py
    admin_controller.py
    ai_controller.py

services/                       # Business logic layer
    auth_service.py             #   Decorator guards, login/logout
    csrf_service.py             #   CSRF token dan validasi request POST
    database_service.py         #   Alembic upgrade, health check, seed
    security_headers_service.py #   Header keamanan response
    rate_limit_service.py       #   Rate limit login, AI, dan chat
    asset_service.py            #   Resolusi asset dev/production manifest
    scoring_service.py          #   Fungsi scoring FP murni
    opportunity_service.py      #   Shared CRUD helpers
    application_service.py      #   Lamaran logic
    document_service.py         #   Dokumen logic
    chat_service.py             #   Chat logic
    ai_service.py               #   Google Gemini integration
    profile_service.py          #   Profil logic
    recruiter_service.py        #   Recruiter-specific logic
    storage_service.py          #   File upload/download
    template_context_service.py #   Global template variables
    constants.py                #   Constants

routes/                         # Legacy/compatibility copy; runtime aktif memakai controllers/
    auth_routes.py
    public_routes.py
    dashboard_routes.py
    opportunity_routes.py
    application_routes.py
    document_routes.py
    profile_routes.py
    chat_routes.py
    recruiter_routes.py
    admin_routes.py
    ai_routes.py

templates/                      # Jinja templates
    base.html                   #   Layout utama
    partials/                   #   Partial components
    auth/
    student/
    recruiter/
    admin/

static/
    css/
        style.css               #   Entrypoint (imports partials)
        partials/               #   34 modular CSS partials
    dist/                       #   Hasil build production + source map
    js/
        app.js                  #   Global handlers (data-confirm, data-pct, dll)
        chat.js                 #   Chat logic
    img/                        #   Gambar dan ilustrasi

uploads/documents/              # File upload (git-ignored)
tests/                          # Unit tests
tools/                          # Utility scripts
deploy/                         # Deployment config
```

Detail aturan akses ada di `docs/access-control.md`.

Detail arsitektur layer, aturan penempatan kode, dan checklist fitur baru ada di `docs/architecture.md`.

## Refactoring Highlights

Proyek telah melalui refactoring untuk menghilangkan spaghetti code:

- **Auth guards**: 25+ inline 3-line guard checks diganti dengan 5 decorator reusable di `services/auth_service.py`
- **CRUD helpers**: Fungsi shared `create_opportunity`, `update_opportunity`, `delete_opportunity_with_cascade` di `services/opportunity_service.py` — mengurangi duplikasi di admin dan recruiter routes
- **Database init**: `init_database()` 230 baris dipecah jadi 8 sub-fungsi
- **Frontend JS**: 514 baris inline `<script>` dari `chat.html` diekstrak ke `static/js/chat.js`
- **Inline handlers**: Semua `onsubmit`, `onclick`, `onchange` diganti data attributes (`data-confirm`, `data-sync-select`, `data-set-value`)
- **Inline styles**: Semua `style="width: X%"` dan `style="--percent: X%"` diganti `data-pct` + CSS variable `--pct`
- **Security hardening**: CSRF, admin-only health endpoint, logout POST-only, security headers, dan cookie hardening
- **Asset pipeline**: CSS/JS production dibuild ke `static/dist/` dengan hash filename, source map, lint ringan, dan build otomatis di deploy

## Validasi Lokal

Jalankan sebelum push/deploy:

```powershell
python tools\lint_frontend_assets.py
python tools\build_frontend_assets.py
python -m pytest -q
```

## Route Penting Untuk Diuji

Umum:
- `/help`

Student:
- `/register`, `/login`, `/logout`
- `/dashboard`
- `/opportunities`, `/opportunities/<id>`
- `/bookmarks`
- `/applications`
- `/documents`
- `/profile`
- `/chat`
- `/ai-assistant`

Recruiter:
- `/recruiter/dashboard`
- `/recruiter/opportunities`
- `/recruiter/applicants`
- `/recruiter/applicants/<id>`

Admin:
- `/admin`
- `/admin/opportunities`
- `/admin/opportunities/create`

Error handling:
- `/opportunities/999999`
- `/admin/opportunities/999999/edit`

## Upload Dokumen

File disimpan di:

```text
uploads/documents/
```

Format: `pdf, doc, docx, png, jpg, jpeg` — Maks 5 MB per file.

File upload tidak ikut commit (diatur `.gitignore`).

## Troubleshooting

Jika error socket/reloader di Windows, jalankan langsung dari terminal:

```powershell
python app.py
```

Proyek sudah memakai `use_reloader=False` agar stabil untuk eksekusi lokal di Windows.
