# Pathora — Smart Internship & Scholarship Tracker

Aplikasi web Flask untuk membantu mahasiswa menemukan peluang magang/beasiswa, melacak lamaran, mengelola dokumen, dan mendapatkan rekomendasi berbasis skor prioritas. Juga menyediakan dashboard rekruter untuk mengelola pelamar.

## Teknologi

- Python 3.12
- Flask 3.0
- SQLite
- Google Gemini API (AI Assistant)
- Gunicorn (deploy production)
- HTML, CSS, JavaScript
- Jinja Template

## Cara Menjalankan Lokal

```powershell
python -m pip install -r requirements.txt
python app.py
```

Buka:

```text
http://127.0.0.1:5000
```

Database SQLite dan folder `uploads/documents/` akan dibuat otomatis saat pertama kali dijalankan.

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

Admin dibuat otomatis jika belum ada. Password disimpan dalam bentuk hash.

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

### Recruiter
- Dashboard rekruter dengan ringkasan pelamar
- Mengelola lowongan (CRUD)
- Melihat daftar pelamar per lowongan
- Mengubah status lamaran (Ditinjau/Diterima/Ditolak)
- Chat dengan pelamar
- Melihat profil dan dokumen pelamar

### Admin
- Semua akses recruiter
- Mengelola seluruh lowongan dari semua recruiter
- Melihat ringkasan jumlah internship/scholarship
- Menghapus lowongan dengan cascade

## Fitur Utama

- Authentication dengan Flask session
- Role-based access control (decorator guards)
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
- Frontend asset build dengan hash filename, source map, dan lint ringan
- Admin & Recruiter CRUD opportunities
- Error page 404, 403, 413
- Mobile responsive

## Konfigurasi Production Penting

Set environment variable berikut sebelum deploy:

```text
SECRET_KEY=<random panjang>
ADMIN_PASSWORD=<password admin yang kuat>
DATA_DIR=/app/data
USE_BUILT_ASSETS=true
GOOGLE_API_KEY=<isi lewat dashboard hosting>
```

Catatan:
- `SECRET_KEY` wajib di production untuk menjaga session tetap aman.
- `ADMIN_PASSWORD` wajib di production; fallback `admin12345` hanya untuk development/test.
- `USE_BUILT_ASSETS=true` membuat template memakai file di `static/dist/`.
- Jika memakai Railway, `Procfile` sudah menjalankan build asset sebelum Gunicorn.

## Struktur Proyek

```text
app.py                          # Entry point + factory create_app()
config.py                       # Konfigurasi (upload folder, db path, dll)
requirements.txt                # Dependencies Python

database/
    schema.sql                  # DDL SQLite

models/                         # Data classes
    user.py
    opportunity.py
    document.py

services/                       # Business logic layer
    auth_service.py             #   Decorator guards, login/logout
    csrf_service.py             #   CSRF token dan validasi request POST
    database_service.py         #   Init DB, migrasi, seed
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

routes/                         # Blueprint-style route modules
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
