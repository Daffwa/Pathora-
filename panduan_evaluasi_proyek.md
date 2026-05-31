# PANDUAN EVALUASI & DOKUMENTASI TEKNIS PROYEK
## Pathora — Smart Internship & Scholarship Tracker

Catatan ini disusun sebagai acuan komprehensif bagi Anda untuk mengirimkan berkas kode (*open code*) dan dokumentasi analisis (*codex*) untuk kebutuhan evaluasi atau penilaian proyek secara lengkap. Dokumen ini merangkum seluruh arsitektur, fitur utama sains data (scoring & AI), instruksi pengujian, serta analisis kesiapan aplikasi.

---

## 1. STRUKTUR BERKAS UTAMA (*OPEN CODE*)

Untuk memudahkan tim penguji memahami berkas kode Anda, berikut adalah struktur modular utama proyek Pathora yang telah dikelompokkan secara bersih:

```text
Project website/
├── app.py                          # Entry point aplikasi & inisialisasi Flask
├── config.py                       # Pusat konfigurasi (database path, upload limit, dll)
├── requirements.txt                # Daftar dependensi modul Python
├── Procfile                        # Konfigurasi WSGI Gunicorn untuk deployment Railway
│
├── database/
│   └── schema.sql                  # Struktur DDL SQLite untuk seluruh tabel utama
│
├── models/                         # Representasi Data Class
│   ├── user.py
│   ├── opportunity.py
│   └── document.py
│
├── services/                       # Logika Bisnis & Komputasi Terpisah
│   ├── scoring_service.py          # Perhitungan Formula Priority Score & Skill Match
│   ├── auth_service.py             # Dekorator Auth Guards & manajemen session
│   ├── database_service.py         # Inisialisasi DB, migrasi, dan seed data awal
│   ├── ai_service.py               # Integrasi Google GenAI SDK (Gemini API)
│   └── chat_service.py             # Penanganan database chat & pesan
│
├── routes/                         # Pengendali Endpoint (Blueprint-style)
│   ├── auth_routes.py              # Logika login & registrasi terpisah per-role
│   ├── opportunity_routes.py       # Discovery, filter, sort, dan bookmark lowongan
│   ├── recruiter_routes.py         # Dashboard rekruter, CRUD lowongan, & kelola pelamar
│   ├── ai_routes.py                # Endpoint API AI Assistant (/api/assistant)
│   └── chat_routes.py              # Endpoint pengiriman pesan & unggah gambar chat
│
└── static/                         # Aset Statis & Frontend Controller
    ├── css/style.css               # CSS entrypoint (mengimpor modular CSS partials)
    └── js/
        ├── app.js                  # Handler event HTML5 data-* global (Clean UI)
        ├── chat.js                 # Controller logika tampilan & validasi berkas chat
        └── ai_assistant.js         # Handler panel asisten AI drag-and-drop
```

---

## 2. LOGIKA UTAMA SAINS DATA & AI (*CODEX LOGIC*)

Sebagai bagian dari evaluasi aplikasi sains data, berikut adalah penjelasan dua pilar logika utama yang digunakan Pathora:

### A. Algoritma Rule-Based Priority Scoring
Aplikasi menghitung prioritas lamaran bagi mahasiswa secara deterministik menggunakan kombinasi tiga parameter utama dengan bobot berbeda di `services/scoring_service.py`:

$$\text{Priority Score} = (\text{Deadline Score} \times 0.40) + (\text{Skill Match Score} \times 0.35) + (\text{Document Score} \times 0.25)$$

1.  **Deadline Score (Bobot 40%):** Dihitung berdasarkan sisa hari menuju penutupan:
    *   $\le 7$ hari: Skor 100 (Sangat mendesak)
    *   $\le 14$ hari: Skor 80
    *   $\le 30$ hari: Skor 60
    *   $> 30$ hari: Skor 40
2.  **Skill Match Score (Bobot 35%):** Menghitung persentase irisan antara himpunan keahlian mahasiswa dengan keahlian yang disyaratkan oleh lowongan (menggunakan string intersection setelah normalisasi huruf kecil).
3.  **Document Score (Bobot 25%):** Dihitung berdasarkan rasio berkas dokumen yang telah diunggah lengkap oleh mahasiswa dibandingkan dengan dokumen wajib.

Hasil akhir diklasifikasikan menjadi tiga label prioritas:
*   $\ge 80$: **High Priority**
*   $\ge 60$: **Medium Priority**
*   $< 60$: **Low Priority**
*   Jika melewati deadline: **Closed**

### B. Asisten AI Terintegrasi
*   **Teknologi:** Google GenAI SDK (`google-genai`) dengan model LLM default `gemma-4-26b-a4b-it` (dapat dikonfigurasi melalui `.env`).
*   **Prompt Engineering:** Diberikan instruksi sistem (*system instructions*) yang membatasi jawaban AI hanya seputar penggunaan platform Pathora untuk menjaga efisiensi dan keamanan.
*   **Keamanan Input:** AI dilengkapi dengan filter pendeteksi konten sensitif (`contains_sensitive_ai_content`) di `services/ai_service.py` untuk mencegah pengguna mengirimkan password, OTP, atau kunci API.

---

## 3. PANDUAN PENGUJIAN EVALUASI (*MANUAL VERIFICATION FLOW*)

Untuk melakukan verifikasi fitur secara menyeluruh selama proses evaluasi, penguji dapat mengikuti skenario uji berikut:

### Skenario 1: Autentikasi & Registrasi Multi-Role
1.  Buka `/register`. Lakukan registrasi akun baru dengan memilih peran **Jobseeker** (isi data akademik & keahlian) dan satu akun untuk peran **Recruiter** (isi nama instansi/perusahaan & jabatan).
2.  Pastikan alur registrasi mengarahkan pengguna ke dashboard yang tepat (Jobseeker ke `/dashboard`, Recruiter ke `/recruiter/dashboard`).
3.  Uji coba logout dan login kembali untuk memastikan penanganan sesi (*session guard*) berjalan normal.

### Skenario 2: Discovery Lowongan & Fitur Sains Data (Mahasiswa)
1.  Masuk sebagai **Jobseeker**. Buka menu **Peluang** (`/opportunities`).
2.  Coba lakukan pencarian kata kunci, lakukan penyaringan (filter) berdasarkan lokasi dan tipe lowongan, serta urutkan berdasarkan *Deadline* atau *Priority Score*.
3.  Buka detail lowongan, tekan tombol **Bookmark** untuk menyimpan peluang ke daftar favorit (`/bookmarks`), lalu tekan **Track Lamaran** untuk memasukkan ke pelacakan status.
4.  Buka menu **Kelola Dokumen** (`/documents`). Unggah contoh berkas CV dan transkrip (maksimal 5 MB). Perhatikan peningkatan persentase kelengkapan dokumen pada dashboard dan kalkulasi *Priority Score* yang meningkat secara dinamis.

### Skenario 3: Manajemen Lowongan & Evaluasi Pelamar (Rekruter)
1.  Masuk sebagai **Recruiter**. Buka menu **Kelola Peluang** (`/recruiter/opportunities/create`) dan buat lowongan baru dengan menentukan daftar keahlian wajib (*required skills*).
2.  Buka menu **Daftar Pelamar** (`/recruiter/applicants`). Gunakan pengurutan berdasarkan **Skill Match** untuk melihat urutan kandidat berdasarkan persentase kecocokan keahlian tertinggi.
3.  Buka salah satu pelamar (`/recruiter/applicants/<id>`), ubah status lamaran (misal dari "Ditinjau" menjadi "Diterima"), lalu periksa apakah status pada dashboard mahasiswa ikut terbarui secara konsisten.
4.  Gunakan fitur **Ekspor CSV** untuk mengunduh rekapitulasi data pelamar dalam format tabel.

### Skenario 4: Asisten AI & Komunikasi Chat
1.  Klik ikon **Asisten AI** di pojok kanan bawah halaman. Kirim pertanyaan seperti: *"Bagaimana cara mengunggah dokumen CV di Pathora?"* dan periksa keakuratan jawaban AI.
2.  Buka menu **Chat** (`/chat`). Kirimkan pesan teks serta lampiran gambar kepada akun pelamar/rekruter untuk memverifikasi fungsionalitas kirim berkas gambar.

---

## 4. INSTALASI LOKAL & DEPLOYMENT

### A. Menjalankan di Komputer Lokal (Windows PowerShell)
```powershell
# 1. Unduh dan ekstrak source code proyek
cd "Project website"

# 2. Instalasi modul dependensi yang dibutuhkan
python -m pip install -r requirements.txt

# 3. Jalankan aplikasi Flask lokal
python app.py
```
Akses melalui peramban di: `http://127.0.0.1:5000`

### B. Environment Variables Kunci (File `.env`)
Pastikan variabel lingkungan berikut telah terkonfigurasi dengan benar agar fitur kecerdasan buatan dapat aktif:
```env
FLASK_DEBUG=True
SECRET_KEY=kunci_rahasia_untuk_keamanan_session_anda
GOOGLE_API_KEY=isi_dengan_gemini_api_key_anda
GOOGLE_MODEL=gemma-4-26b-a4b-it
GOOGLE_TIMEOUT_SECONDS=120
```

---

## 5. ANALISIS KEKURANGAN & GAP PENGEMBANGAN (UNTUK BAHAN DISKUSI EVALUASI)

Sebagai nilai tambah dalam laporan evaluasi, Anda dapat menyertakan beberapa poin keterbatasan teknis saat ini yang dapat dijadikan rencana pengembangan jangka panjang (*future works*):

1.  **Mekanisme Real-Time Chat:** Komunikasi chat saat ini masih menggunakan HTTP Request reguler (`fetch/AJAX`). Idealnya, untuk aplikasi berskala besar, sistem ini ditingkatkan menggunakan **WebSocket** agar pengiriman pesan terjadi seketika tanpa perlu membebani server dengan request berkala.
2.  **Notifikasi yang Masih Hardcoded:** Komponen notifikasi cepat di *topbar* saat ini masih menggunakan representasi statis. Disarankan untuk menambahkan tabel `notifications` pada basis data untuk mendukung perekaman aktivitas penting secara dinamis.
3.  **Skalabilitas SQLite:** Database berbasis file SQLite sangat baik untuk tahap purwarupa (prototipe). Namun, untuk evaluasi skala komersial, disarankan melakukan migrasi ke sistem database server seperti **PostgreSQL** guna mencegah kendala *database locking* pada lalu lintas pengguna yang padat.
4.  **Fitur Sosial & Autentikasi Tambahan:** Tombol masuk via *Google* & *LinkedIn* serta fitur *Lupa Password* saat ini baru berupa antarmuka statis dan memerlukan implementasi library otentikasi (OAuth2) untuk dapat berfungsi sepenuhnya di lingkungan produksi.
