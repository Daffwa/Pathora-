# Dokumentasi Skenario Penggunaan Web ScholarTrack

## 1. Judul Dokumentasi

**Dokumentasi Skenario Penggunaan Web ScholarTrack**

## 2. Ringkasan Aplikasi

ScholarTrack atau Smart Internship & Scholarship Tracker adalah aplikasi web lokal berbasis Flask yang membantu mahasiswa mencari peluang internship dan scholarship, menyimpan peluang yang menarik, melacak progres lamaran, mengelola dokumen persyaratan, serta melihat priority score berdasarkan deadline, kecocokan skill, dan kelengkapan dokumen.

Pengguna utama aplikasi ini adalah mahasiswa atau jobseeker yang sedang mencari peluang akademik dan karier. Aplikasi juga menyediakan role admin untuk mengelola data peluang, serta role recruiter/HRD yang ditemukan di kode untuk membuat lowongan dan melihat applicant.

Manfaat aplikasi bagi mahasiswa adalah membuat proses pencarian peluang lebih terstruktur. Mahasiswa tidak hanya melihat daftar peluang, tetapi juga dapat menyimpan peluang, menambahkan peluang ke application tracker, memperbarui status lamaran, mengecek dokumen yang belum lengkap, dan memprioritaskan peluang yang paling relevan.

## 3. Daftar Role Pengguna

| Role | Hak akses | Batasan |
|---|---|---|
| Guest / pengguna belum login | Dapat membuka landing page, halaman daftar peluang, detail peluang, login, dan register. | Tidak dapat menyimpan peluang, menambahkan tracker, mengelola dokumen, membuka dashboard student, membuka profile, atau mengakses halaman admin. |
| Student / user mahasiswa | Di kode disebut `jobseeker`. Dapat register, login, logout, membuka dashboard, mencari peluang, melihat detail peluang, bookmark peluang, track lamaran, mengubah status lamaran, mengelola dokumen, melihat priority score, dan mengelola profile. | Tidak dapat membuka halaman admin. Tidak dapat mengakses halaman recruiter. |
| Admin | Dapat login sebagai admin, membuka dashboard admin, melihat ringkasan peluang, serta menambah, mengedit, dan menghapus opportunity. | Tidak memiliki fitur tracker personal student pada UI admin. Akses admin hanya untuk akun dengan role `admin`. |

Catatan: kode juga memiliki role `recruiter` atau Recruiter / HRD. Role ini dapat membuat lowongan, mengelola lowongan miliknya, melihat applicant, dan mengubah status applicant. Role recruiter tidak diminta sebagai role utama pada tabel di atas, tetapi tetap dicatat pada daftar route karena memang tersedia di proyek.

## 4. Daftar Halaman / Route Web

| Nama halaman | Route / URL | Role yang dapat mengakses | Fungsi halaman | Status |
|---|---|---|---|---|
| Landing page | `/` | Guest, semua user | Halaman awal/public ScholarTrack. | Tersedia |
| Login | `/login` | Guest | Form login dan redirect sesuai role. | Tersedia |
| Register | `/register` | Guest | Form pendaftaran jobseeker atau recruiter. | Tersedia |
| Logout | `/logout` | User login | Menghapus session dan kembali ke login. | Tersedia |
| Avatar profile | `/uploads/avatars/<filename>` | User login | Menampilkan file avatar dari folder upload. | Tersedia |
| AI assistant chat | `/ai-assistant/chat` | User login | API chat sederhana berbasis konteks role. | Tersedia |
| Dashboard student | `/dashboard` | Student / jobseeker | Ringkasan saved, applications, documents, urgent deadlines, dan rekomendasi prioritas. | Tersedia |
| Daftar peluang | `/opportunities` | Guest, Student, Admin, Recruiter | Menampilkan peluang dengan search, filter type/lokasi, dan sort deadline/priority. | Tersedia |
| Detail peluang | `/opportunities/<id>` | Guest, Student, Admin, Recruiter | Menampilkan detail peluang, deadline, persyaratan, skill, link resmi, dan priority score untuk jobseeker. | Tersedia |
| Simpan bookmark | `/opportunities/<id>/bookmark` | Student / jobseeker | Menyimpan peluang ke tabel bookmark. | Tersedia |
| Hapus bookmark | `/bookmarks/<id>/remove` | Student / jobseeker | Menghapus peluang dari saved opportunities. | Tersedia |
| Saved opportunities | `/bookmarks` | Student / jobseeker | Redirect ke bagian saved opportunities pada profile. | Tersedia |
| Tambah tracker | `/opportunities/<id>/track` | Student / jobseeker | Menambahkan peluang ke application tracker. | Tersedia |
| Application tracker | `/applications` | Student / jobseeker | Menampilkan daftar lamaran yang sedang dipantau. | Tersedia |
| Update application | `/applications/<id>/update` | Student / jobseeker | Mengubah status dan catatan lamaran. | Tersedia |
| Hapus application | `/applications/<id>/remove` | Student / jobseeker | Menghapus tracker lamaran. | Tersedia |
| Document tracker | `/documents` | Student / jobseeker | Menampilkan checklist dokumen CV, transkrip, sertifikat, motivation letter, portofolio, dan KTP/KTM. | Tersedia |
| Update document | `/documents/<doc_type>/update` | Student / jobseeker | Menandai dokumen tersedia, upload file, dan menyimpan catatan. | Tersedia |
| Reset document | `/documents/<doc_type>/reset` | Student / jobseeker | Menghapus status/file/catatan dokumen. | Tersedia |
| Download/view document | `/documents/<doc_type>/download` | Student / jobseeker | Menampilkan file dokumen yang sudah diupload. | Tersedia |
| Profile | `/profile` | Student / jobseeker | Menampilkan identitas, pendidikan, skill, saved opportunities, dan kelengkapan profile. | Tersedia |
| Edit profile | `/profile/edit` | Student / jobseeker | Mengubah data pribadi, akademik, karier, skill, link, avatar, dan password. | Tersedia |
| Recruiter dashboard | `/recruiter/dashboard` | Recruiter / HRD | Ringkasan lowongan dan applicant milik recruiter. | Tersedia |
| Recruiter opportunities | `/recruiter/opportunities` | Recruiter / HRD | Daftar lowongan yang dibuat recruiter. | Tersedia |
| Recruiter create opportunity | `/recruiter/opportunities/create` | Recruiter / HRD | Membuat lowongan baru. | Tersedia |
| Recruiter edit opportunity | `/recruiter/opportunities/<id>/edit` | Recruiter / HRD | Mengedit lowongan milik recruiter. | Tersedia |
| Recruiter delete opportunity | `/recruiter/opportunities/<id>/delete` | Recruiter / HRD | Menghapus lowongan milik recruiter. | Tersedia |
| Recruiter applicants | `/recruiter/applicants` | Recruiter / HRD | Melihat daftar applicant dari lowongan recruiter. | Tersedia |
| Recruiter applicants per peluang | `/recruiter/opportunities/<id>/applicants` | Recruiter / HRD | Melihat applicant untuk satu lowongan. | Tersedia |
| Recruiter applicant detail | `/recruiter/applicants/<application_id>` | Recruiter / HRD | Melihat detail applicant dan status dokumen. | Tersedia |
| Recruiter update applicant status | `/recruiter/applications/<application_id>/status` | Recruiter / HRD | Mengubah status applicant. | Tersedia |
| Admin dashboard | `/admin` | Admin | Ringkasan total opportunity, internship, dan scholarship. | Tersedia |
| Admin manage opportunities | `/admin/opportunities` | Admin | Melihat seluruh data peluang. | Tersedia |
| Admin create opportunity | `/admin/opportunities/create` | Admin | Menambah peluang baru. | Tersedia |
| Admin edit opportunity | `/admin/opportunities/<id>/edit` | Admin | Mengubah data peluang. | Tersedia |
| Admin delete opportunity | `/admin/opportunities/<id>/delete` | Admin | Menghapus peluang beserta bookmark dan application terkait. | Tersedia |
| Halaman 404 | Error handler `404` | Semua role | Menampilkan halaman jika data atau route tidak ditemukan. | Tersedia |
| Halaman 403 | Error handler `403` | Semua role | Menampilkan halaman jika user tidak memiliki izin akses. | Tersedia |

Catatan: filter deadline dalam bentuk rentang tanggal belum ditemukan. Yang tersedia adalah pengurutan berdasarkan deadline (`sort=deadline`) dan indikator deadline seperti Open, Urgent, atau Closed.

## 5. Skenario Utama Penggunaan Web

| ID skenario | Nama skenario | Aktor | Tujuan | Prasyarat | Langkah-langkah | Hasil yang diharapkan | Data yang terlibat | Catatan validasi/error handling |
|---|---|---|---|---|---|---|---|---|
| S-01 | Register akun mahasiswa | Guest | Membuat akun student/jobseeker. | User belum login dan email belum terdaftar. | Buka `/register`.<br>Pilih role Jobseeker.<br>Isi nama, email, skills, password, dan confirm password.<br>Klik Register. | Data user baru tersimpan dan user diarahkan ke halaman login. | Tabel `users`: name, email, skills, password_hash, role. | Sistem menolak nama/email/password kosong, password tidak sama, role tidak valid, dan email yang sudah terdaftar. Validasi format email server-side khusus belum ditemukan, tetapi input HTML memakai `type=email`. |
| S-02 | Login dan logout | Student/Admin/Recruiter | Masuk ke aplikasi sesuai role dan keluar dari session. | User sudah terdaftar. | Buka `/login`.<br>Isi email dan password.<br>Klik Login.<br>Setelah berhasil, klik Logout. | Student diarahkan ke `/dashboard`, admin ke `/admin`, recruiter ke `/recruiter/dashboard`. Logout menghapus session dan kembali ke `/login`. | Tabel `users`, Flask `session`. | Jika email/password salah, tampil pesan "Email atau password tidak sesuai". Jika role tidak valid, login ditolak. |
| S-03 | Melihat dashboard utama | Student / jobseeker | Melihat ringkasan progres pencarian peluang. | Student sudah login. | Buka `/dashboard`. | Dashboard menampilkan total saved, total applications, dokumen lengkap, urgent deadlines, recent saved, recent applications, dan rekomendasi prioritas. | Tabel `bookmarks`, `applications`, `documents`, `opportunities`. | Jika belum login atau bukan jobseeker, sistem meminta login jobseeker atau menolak akses. |
| S-04 | Mencari peluang internship/scholarship | Guest atau Student | Menemukan peluang berdasarkan kata kunci. | Data opportunity tersedia. | Buka `/opportunities`.<br>Isi keyword pada field search.<br>Klik Filter. | Sistem menampilkan peluang yang title, organizer, lokasi, atau deskripsinya cocok dengan keyword. | Tabel `opportunities`, parameter query `q`. | Jika tidak ada hasil, halaman menampilkan empty state "Tidak ada peluang cocok". |
| S-05 | Filter peluang berdasarkan tipe, lokasi, deadline, atau keyword | Guest atau Student | Mempersempit daftar peluang. | Data opportunity tersedia. | Buka `/opportunities`.<br>Pilih type internship/scholarship.<br>Pilih location.<br>Isi keyword bila perlu.<br>Pilih sort Deadline atau Priority.<br>Klik Filter. | Daftar peluang tampil sesuai keyword, type, lokasi, dan urutan deadline atau priority. | Tabel `opportunities`, parameter `q`, `type`, `location`, `sort`. | Filter deadline berbasis tanggal/range belum tersedia; yang ada adalah sort deadline. Sort priority hanya efektif untuk jobseeker karena perlu scoring context. |
| S-06 | Melihat detail peluang | Guest atau Student | Membaca informasi lengkap suatu peluang. | Opportunity dengan ID terkait tersedia. | Dari `/opportunities`, klik Detail.<br>Buka `/opportunities/<id>`. | Halaman menampilkan judul, provider, lokasi, tipe, deskripsi, persyaratan, skill, deadline, official link jika ada, dan priority score untuk jobseeker. | Tabel `opportunities`, scoring context user. | Jika ID peluang tidak ditemukan, sistem menampilkan 404. Guest dapat melihat detail, tetapi tidak dapat menyimpan atau track. |
| S-07 | Menyimpan peluang ke bookmark | Student / jobseeker | Menyimpan peluang yang menarik. | Student sudah login dan peluang tersedia. | Buka daftar/detail peluang.<br>Klik Simpan atau Simpan peluang. | Data bookmark tersimpan dan peluang muncul di bagian saved opportunities pada profile. | Tabel `bookmarks`, `opportunities`, `users`. | Duplikasi bookmark dicegah oleh unique constraint dan ditangani dengan pesan "Peluang ini sudah ada di Saved Opportunities." |
| S-08 | Menambahkan peluang ke application tracker | Student / jobseeker | Memantau proses lamaran untuk peluang tertentu. | Student sudah login dan peluang tersedia. | Buka detail peluang atau saved opportunities.<br>Klik Track Lamaran/Track. | Sistem membuat application dengan status awal "Belum Daftar" dan mengarahkan ke `/applications`. | Tabel `applications`, `opportunities`, `users`. | Duplikasi tracker dicegah oleh unique constraint dan ditangani dengan pesan "Peluang ini sudah ada di Application Tracker." |
| S-09 | Mengubah status lamaran | Student / jobseeker | Memperbarui progres lamaran. | Student sudah memiliki application tracker. | Buka `/applications`.<br>Pilih status dari dropdown.<br>Isi notes bila perlu.<br>Klik Update. | Status dan catatan lamaran berubah, `updated_at` diperbarui. | Tabel `applications`, daftar `APPLICATION_STATUSES`. | Jika status tidak termasuk daftar valid, sistem menampilkan pesan "Status tidak valid." |
| S-10 | Mengelola dokumen persyaratan | Student / jobseeker | Menandai dan mengunggah dokumen penting. | Student sudah login. | Buka `/documents`.<br>Pilih dokumen seperti CV atau Transkrip.<br>Centang tersedia, upload file, isi notes.<br>Klik Update. | Dokumen tersimpan sebagai uploaded, progress dokumen bertambah, file dapat dilihat melalui link dokumen. | Tabel `documents`, folder `uploads/documents`. | Tipe dokumen tidak valid menghasilkan 404. Format file hanya pdf, doc, docx, png, jpg, jpeg. Ukuran maksimal file 5 MB. |
| S-11 | Menghitung atau menampilkan priority score | Student / jobseeker | Mengetahui peluang yang perlu diprioritaskan. | Student login, memiliki data skill dan/atau dokumen. | Buka dashboard, daftar peluang, atau detail peluang.<br>Lihat match score/priority score. | Sistem menampilkan score dan label priority berdasarkan deadline score, skill match score, dan document score. | `services/scoring_service.py`, tabel `users`, `documents`, `opportunities`. | Formula yang ditemukan: 40% deadline, 35% skill, 25% dokumen. Jika peluang closed, label menjadi Closed. Guest tidak melihat score personal. |
| S-12 | Mengelola profile user | Student / jobseeker | Melengkapi identitas dan data pendukung rekomendasi. | Student sudah login. | Buka `/profile`.<br>Klik Edit Profil.<br>Ubah data pribadi, akademik, karier, skill, link, avatar, atau password.<br>Klik Simpan Perubahan. | Profile diperbarui dan kelengkapan profile dapat meningkat. | Tabel `users`, folder `uploads/avatars`. | Sistem memvalidasi nama/email wajib, email unik, tanggal lahir, IPK 0.00-4.00, semester 1-14, tahun masuk, password baru minimal 8 karakter, serta format avatar jpg/jpeg/png. |
| S-13 | Admin menambah, mengedit, dan menghapus peluang | Admin | Mengelola data opportunity yang tampil ke user. | Admin sudah login. | Buka `/admin`.<br>Masuk ke `/admin/opportunities`.<br>Klik Tambah Peluang, isi form, simpan.<br>Klik Edit untuk mengubah.<br>Klik Delete untuk menghapus. | Data peluang bertambah, berubah, atau terhapus sesuai aksi admin. | Tabel `opportunities`, serta `bookmarks` dan `applications` saat delete. | Form admin memvalidasi title, type, organizer, location, dan deadline. Jika database error, muncul pesan gagal. |
| S-14 | Pencegahan akses admin oleh user biasa | Student / jobseeker | Memastikan halaman admin terlindungi. | Student sudah login. | Student mencoba membuka `/admin` atau `/admin/opportunities`. | Sistem menolak akses dan menampilkan halaman 403. | Flask session, role user, decorator `admin_required`. | Fungsi `role_required` melakukan abort 403 jika role tidak sesuai. |
| S-15 | Recruiter mengelola lowongan dan applicant | Recruiter / HRD | Mengelola lowongan milik perusahaan dan melihat applicant. | Recruiter sudah login. | Buka `/recruiter/dashboard`.<br>Buka My Job Posts.<br>Tambah/edit/hapus lowongan.<br>Buka Applicants dan ubah status applicant. | Recruiter dapat mengelola lowongan miliknya dan memperbarui status applicant. | Tabel `opportunities`, `applications`, `users`, `documents`. | Recruiter hanya dapat mengedit/menghapus opportunity yang `created_by` sesuai user login. |

## 6. Alur End-to-End Pengguna

Seorang mahasiswa membuka web ScholarTrack, melakukan registrasi sebagai jobseeker, lalu login ke dashboard. Setelah masuk, mahasiswa mencari peluang "Data Science Internship" pada halaman peluang, menggunakan filter keyword, type, lokasi, dan sort deadline untuk menemukan peluang yang relevan. Mahasiswa kemudian membuka detail peluang, menyimpan peluang tersebut ke bookmark, menambahkannya ke application tracker, melengkapi dokumen seperti CV dan transkrip pada Document Tracker, melihat priority score untuk menentukan prioritas, lalu memperbarui status lamaran dari "Belum Daftar" menjadi status yang sesuai dengan progresnya.

## 7. Skenario Negatif / Error Handling

| Kasus negatif | Kondisi | Respons aplikasi yang ditemukan | Status |
|---|---|---|---|
| Email sudah terdaftar | Register memakai email yang sudah ada di tabel `users`. | Sistem menampilkan pesan "Email sudah terdaftar. Gunakan email lain atau login." dan mengembalikan status 409. | Tersedia |
| Password salah | Login dengan email benar tetapi password salah. | Sistem menampilkan pesan "Email atau password tidak sesuai. Silakan coba lagi." dan mengembalikan status 401. | Tersedia |
| Format email tidak valid | User memasukkan email tidak valid pada form. | Input HTML memakai `type=email`, tetapi validasi format email khusus di server belum ditemukan. | Perlu dikembangkan |
| Keyword pencarian tidak ditemukan | Search/filter tidak menghasilkan data peluang. | Halaman menampilkan empty state "Tidak ada peluang cocok" dan tombol reset filter. | Tersedia |
| Bookmark duplikat | User menyimpan peluang yang sama lebih dari sekali. | Unique constraint `(user_id, opportunity_id)` memicu `sqlite3.IntegrityError`, lalu muncul pesan peluang sudah ada di Saved Opportunities. | Tersedia |
| Status lamaran tidak valid | Request update application mengirim status di luar daftar valid. | Sistem menampilkan pesan "Status tidak valid." dan tidak memperbarui data. | Tersedia |
| Dokumen belum lengkap | User belum mengunggah/menandai seluruh dokumen. | Dashboard dan Document Tracker menampilkan progres dokumen, misalnya `x/6`; aplikasi belum memblokir pendaftaran jika dokumen belum lengkap. | Tersedia, validasi blokir belum tersedia |
| User biasa mencoba membuka halaman admin | Student membuka `/admin` atau route admin lain. | Sistem melakukan abort 403 dan menampilkan halaman 403. | Tersedia |
| Data peluang tidak ditemukan | User membuka `/opportunities/<id>` dengan ID yang tidak ada. | Sistem melakukan abort 404 dan menampilkan halaman 404. | Tersedia |
| Database gagal diproses | Operasi insert/update/delete terkena `sqlite3.Error`. | Beberapa route menampilkan pesan gagal seperti "Silakan coba lagi." | Tersedia |
| File gagal diproses | Upload dokumen memakai format tidak didukung, ukuran lebih dari 5 MB, atau file dokumen hilang dari folder upload. | Sistem menampilkan pesan format file tidak didukung, ukuran file terlalu besar, atau file tidak ditemukan. | Tersedia |
| Tipe dokumen tidak valid | User mengakses `/documents/<doc_type>` yang tidak ada dalam daftar dokumen. | Sistem melakukan abort 404. | Tersedia |

## 8. Keterkaitan dengan Konsep PASD

**OOP.** Proyek memakai model berbasis `dataclass` pada folder `models`, yaitu `User`, `Opportunity`, dan `Document`. Class tersebut membantu merepresentasikan data dari database menjadi objek yang lebih rapi. Model khusus `Application` belum ditemukan, tetapi data lamaran sudah tersedia dalam tabel `applications`.

**FP.** Konsep functional programming terlihat pada fungsi-fungsi murni di `services/scoring_service.py`, seperti `calculate_days_left`, `calculate_deadline_score`, `calculate_skill_match_score`, `calculate_document_score`, `calculate_priority_score`, dan `get_priority_label`. Fungsi ini memisahkan logika scoring dari route Flask. Kode juga memakai pola mapping/list comprehension untuk mengubah row database menjadi objek dan menghitung progres dokumen.

**Error handling.** Aplikasi menangani error melalui validasi form, `try-except` untuk database, `sqlite3.IntegrityError` untuk duplikasi bookmark/tracker, handler 404 dan 403, serta handler `RequestEntityTooLarge` untuk file lebih dari 5 MB. Pesan error ditampilkan ke user memakai `flash`.

**Modularity.** Struktur proyek cukup modular: `app.py` untuk route dan controller utama, `config.py` untuk konfigurasi, `database/schema.sql` untuk schema SQLite, folder `models` untuk representasi data, folder `services` untuk scoring, folder `templates` untuk tampilan Jinja, `static` untuk CSS/JavaScript, dan `uploads` untuk file user.

**Readability.** Nama route, fungsi, model, dan template cukup deskriptif, misalnya `update_application`, `get_dashboard_summary`, `get_document_progress_for_user`, dan `calculate_priority_score`. Dokumentasi tambahan ini membantu pembaca laporan memahami fitur dan skenario uji tanpa harus membaca seluruh kode.

**Testing.** Folder atau file automated test belum ditemukan. Namun, skenario pada dokumen ini dapat dipakai sebagai dasar pengujian black box dan end-to-end, mulai dari register, login, pencarian peluang, bookmark, tracker lamaran, dokumen, priority score, sampai pembatasan akses admin.

## 9. Acceptance Criteria

- [ ] User bisa register dan login.
- [ ] User bisa mencari peluang.
- [ ] User bisa bookmark peluang.
- [ ] User bisa tracking lamaran.
- [ ] User bisa melihat dashboard.
- [ ] Admin bisa CRUD peluang.
- [ ] User biasa tidak bisa akses admin.
- [ ] Error input ditangani dengan pesan yang jelas.

Catatan tambahan: sebagian besar acceptance criteria di atas sudah didukung oleh route dan kode yang ditemukan. Validasi format email server-side dan filter deadline berbasis rentang tanggal belum ditemukan sehingga dapat menjadi pengembangan lanjutan.

## 10. Kesimpulan

Dokumentasi skenario penggunaan ini membantu menjelaskan cara kerja ScholarTrack dari sudut pandang pengguna, mulai dari guest, student/jobseeker, admin, sampai role recruiter yang memang tersedia di kode. Dengan skenario yang terstruktur, aplikasi dapat diuji berdasarkan alur nyata mahasiswa ketika mencari, menyimpan, dan melacak peluang internship maupun scholarship.

Secara keseluruhan, skenario ini dapat digunakan sebagai bahan laporan atau presentasi kuliah karena menghubungkan fitur aplikasi dengan kebutuhan mahasiswa dan konsep PASD. Dokumen ini juga membantu menentukan bagian yang sudah tersedia serta bagian yang masih perlu dikembangkan, seperti validasi email server-side, filter deadline berbasis rentang tanggal, dan automated testing.
