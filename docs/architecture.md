# Arsitektur dan Aturan Maintenance Pathora

Dokumen ini menjadi pegangan saat menambah fitur atau membenahi kode Pathora agar struktur tetap konsisten, terutama setelah migrasi ke SQLAlchemy ORM, repository layer, service layer, dan MVC-style Flask.

## Ringkasan Layer

```text
models/        SQLAlchemy ORM untuk tabel database
dto/           Dataclass/view model non-ORM untuk kebutuhan template atau service
repositories/  Query database, insert, update, delete, dan mapping row
services/      Business logic, validasi domain, scoring, auth, storage, dan integrasi API
controllers/   Alur request-response berbasis Flask Blueprint
routes/        Legacy route modules; jangan tambah route baru di sini
templates/     View HTML Jinja
static/        CSS, JavaScript, image, dan hasil build frontend
migrations/    Alembic/Flask-Migrate sebagai sumber perubahan schema database
```

## Aturan Penempatan Kode

- Definisi tabel baru masuk ke `models/`.
- Perubahan schema database wajib lewat `flask db migrate` dan `flask db upgrade`.
- Query database tidak ditulis langsung di controller; taruh di `repositories/`.
- Logika bisnis tidak ditulis langsung di route/template; taruh di `services/`.
- Alur HTTP, session, redirect, flash message, dan render template taruh di `controllers/`.
- Dataclass yang bukan tabel database taruh di `dto/`, bukan di `models/`.
- Template HTML taruh di `templates/`, CSS/JS/gambar taruh di `static/`.
- Jangan menambah akses database baru dengan `sqlite3`, `get_db()`, `PRAGMA`, atau `schema.sql`.

## Catatan Controllers dan Routes

`controllers/` adalah layer aktif yang didaftarkan oleh `app.py` sebagai Blueprint. Folder `routes/` masih ada sebagai modul lama/legacy dari refactor sebelumnya. Untuk fitur baru, gunakan `controllers/` agar pola aplikasi tidak bercabang.

Jika nanti ingin membersihkan lebih jauh, `routes/` dapat dihapus setelah dipastikan tidak ada import, test, atau dokumentasi yang masih bergantung ke sana.

## Checklist Fitur Baru

Untuk fitur yang menambah tabel atau kolom:

1. Tambah atau ubah ORM model di `models/`.
2. Jalankan `flask db migrate -m "deskripsi perubahan"`.
3. Review file migration di `migrations/versions/`.
4. Jalankan `flask db upgrade`.
5. Tambah fungsi query di `repositories/`.
6. Tambah aturan bisnis di `services/`.
7. Tambah endpoint atau halaman di `controllers/`.
8. Tambah atau ubah template di `templates/` dan asset di `static/` jika perlu.
9. Tambah test yang relevan.
10. Jalankan `python -m pytest -q`.

Untuk fitur tanpa perubahan database:

1. Taruh business logic di `services/`.
2. Taruh alur request-response di `controllers/`.
3. Taruh tampilan di `templates/` dan asset di `static/`.
4. Tambah test sesuai risiko perubahan.
5. Jalankan `python -m pytest -q`.

## Pola Import yang Dianjurkan

Repository mengambil ORM dari package `models`:

```python
from models import UserORM
```

Controller/service mengambil dataclass non-ORM dari `dto`:

```python
from dto.opportunity import Opportunity
```

Service atau controller memakai repository untuk membaca/menulis database:

```python
from repositories import user_repository

user = user_repository.find_by_email(email)
```

## Database Production

Production disarankan memakai PostgreSQL atau MySQL melalui `DATABASE_URL`. SQLite tetap tersedia sebagai fallback development lokal jika `DATABASE_URL` tidak diisi.

Contoh:

```text
DATABASE_URL=postgresql://user:password@host:5432/pathora
DATABASE_URL=mysql+pymysql://user:password@host:3306/pathora
```

Pastikan migration Alembic menjadi satu-satunya sumber perubahan schema. Jangan menghidupkan kembali `database/schema.sql` untuk perubahan baru.
