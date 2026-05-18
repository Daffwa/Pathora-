# Smart Internship & Scholarship Tracker

Aplikasi web lokal berbasis Flask untuk membantu mahasiswa mencari peluang internship/scholarship, menyimpan peluang, melacak status lamaran, mengelola dokumen, dan melihat priority score sederhana.

## Teknologi

- Python
- Flask
- SQLite
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

Database SQLite akan dibuat/di-update otomatis melalui `init_database()` saat `python app.py` dijalankan.

## Akun Admin

```text
Email: admin@example.com
Password: admin12345
```

Admin dibuat otomatis jika belum ada. Password disimpan dalam bentuk hash.

## Role dan Akses

Student dapat:
- Register, login, logout
- Melihat, mencari, filter, dan sort peluang
- Menyimpan peluang
- Melacak status lamaran
- Upload dan reset dokumen
- Melihat dashboard dan priority score personal

Admin dapat:
- Mengakses dashboard admin
- Tambah, edit, dan hapus opportunities
- Melihat ringkasan jumlah internship/scholarship

## Fitur Utama

- Authentication dengan Flask session
- Opportunity discovery
- Saved opportunities
- Application tracker
- Document tracker dengan upload lokal
- Smart priority score
- Dashboard ringkasan
- Admin CRUD opportunities
- Error page 404 dan 403

## Struktur Singkat

```text
app.py
config.py
database/schema.sql
models/
services/
templates/
static/css/style.css
uploads/documents/
```

## Dokumentasi OOP

Model sederhana berada di folder `models/`:
- `User`
- `Opportunity`
- `Document`

Model dipakai untuk merepresentasikan data aplikasi agar struktur data lebih mudah dibaca dan dijelaskan.

## Dokumentasi FP

Fungsi scoring berada di:

```text
services/scoring_service.py
```

Fungsi utama:
- `calculate_days_left`
- `calculate_deadline_score`
- `calculate_skill_match_score`
- `calculate_document_score`
- `calculate_priority_score`
- `get_priority_label`

Fungsi ini dibuat terpisah agar mudah dites dan tidak bergantung langsung pada route Flask.

## Route Penting Untuk Diuji

Student:
- `/register`
- `/login`
- `/dashboard`
- `/opportunities`
- `/bookmarks`
- `/applications`
- `/documents`

Admin:
- `/admin`
- `/admin/opportunities`
- `/admin/opportunities/create`

Error handling:
- `/opportunities/999999`
- `/admin/opportunities/999999/edit`

## Upload Dokumen

File dokumen disimpan lokal di:

```text
uploads/documents/
```

File upload user tidak ikut commit karena sudah diatur di `.gitignore`.

Format yang didukung:

```text
pdf, doc, docx, png, jpg, jpeg
```

Ukuran maksimal file: 5 MB.

## Troubleshooting

Jika menjalankan dari VS Code Debug dan muncul error socket/reloader di Windows, jalankan langsung dari terminal:

```powershell
python app.py
```

Project sudah memakai:

```python
app.run(debug=True, use_reloader=False)
```

agar lebih stabil untuk eksekusi lokal di Windows.
