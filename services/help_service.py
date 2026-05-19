HELP_CATEGORIES = [
    "Akun & Login",
    "Profil",
    "Dokumen",
    "Peluang",
    "Bookmark",
    "Pelacakan Lamaran",
    "Chat",
    "Recruiter",
    "Admin",
    "Fitur Segera Hadir",
]

HELP_CONTEXT_LABELS = {
    "dashboard": "Dashboard",
    "documents": "Dokumen",
    "profile": "Profil",
    "opportunities": "Peluang",
    "applications": "Pelacakan Lamaran",
    "chat": "Chat",
    "recruiter": "Recruiter",
    "admin": "Admin",
}

HELP_ARTICLES = [
    {
        "id": "daftar-akun",
        "title": "Cara daftar akun",
        "category": "Akun & Login",
        "summary": "Buat akun Jobseeker atau Recruiter dari halaman Daftar.",
        "body": [
            "Buka halaman Daftar, pilih role Jobseeker atau Recruiter / HRD, lalu isi nama, email, password, dan konfirmasi password.",
            "Untuk akun recruiter, isi nama perusahaan dan posisi. Setelah berhasil, Pathora mengarahkan akun ke dashboard sesuai role.",
        ],
        "keywords": ["daftar", "register", "akun", "jobseeker", "recruiter", "hrd"],
        "contexts": ["dashboard", "recruiter"],
        "roles": ["general"],
        "popular": True,
    },
    {
        "id": "login-akun",
        "title": "Cara login",
        "category": "Akun & Login",
        "summary": "Masuk memakai email dan password yang sudah terdaftar.",
        "body": [
            "Buka halaman Masuk, isi email dan password, lalu klik tombol Masuk.",
            "Jika akun valid, Jobseeker diarahkan ke Dashboard, Recruiter ke Dashboard Recruiter, dan Admin ke halaman Admin.",
            "Google Login, LinkedIn Login, dan Lupa Password belum aktif. Gunakan email dan password manual untuk saat ini.",
        ],
        "keywords": ["login", "masuk", "email", "password", "google", "linkedin", "lupa password"],
        "contexts": ["dashboard", "recruiter", "admin"],
        "roles": ["general"],
        "popular": True,
    },
    {
        "id": "edit-profil",
        "title": "Cara edit profil",
        "category": "Profil",
        "summary": "Lengkapi data diri, skill, minat, dan foto profil dari halaman Edit Profil.",
        "body": [
            "Buka Profil, lalu pilih Edit Profil. Perbarui data seperti nama, email, universitas, jurusan, IPK, skill, minat, dan posisi yang diinginkan.",
            "Foto profil bisa diganti atau dihapus dari form yang sama. Simpan perubahan agar dashboard dan rekomendasi memakai data terbaru.",
        ],
        "keywords": ["profil", "edit", "ubah", "skill", "minat", "foto", "avatar"],
        "contexts": ["profile", "dashboard"],
        "roles": ["jobseeker"],
        "popular": True,
    },
    {
        "id": "upload-dokumen-cv",
        "title": "Cara upload dokumen atau CV",
        "category": "Dokumen",
        "summary": "Unggah CV, transkrip, sertifikat, dan dokumen pendukung dari Kelola Dokumen.",
        "body": [
            "Buka Kelola Dokumen, pilih baris dokumen yang ingin diperbarui, klik Pilih File, lalu klik Unggah.",
            "Format yang didukung adalah PDF, DOC, DOCX, PNG, JPG, dan JPEG. File yang berhasil diunggah akan tampil sebagai dokumen terverifikasi.",
        ],
        "keywords": ["upload", "unggah", "dokumen", "cv", "resume", "transkrip", "sertifikat", "file"],
        "contexts": ["documents", "dashboard", "applications"],
        "roles": ["jobseeker"],
        "popular": True,
    },
    {
        "id": "reset-dokumen",
        "title": "Cara reset dokumen",
        "category": "Dokumen",
        "summary": "Kosongkan dokumen lama saat ingin mulai ulang atau mengganti file.",
        "body": [
            "Buka Kelola Dokumen dan cari dokumen yang sudah terunggah. Klik Reset pada baris dokumen tersebut.",
            "Setelah reset, status dokumen kembali menjadi Belum Ada dan file lama tidak lagi dipakai untuk kebutuhan lamaran.",
        ],
        "keywords": ["reset", "hapus", "dokumen", "cv", "file", "ulang"],
        "contexts": ["documents"],
        "roles": ["jobseeker"],
        "popular": False,
    },
    {
        "id": "cari-peluang",
        "title": "Cara mencari peluang",
        "category": "Peluang",
        "summary": "Gunakan halaman Peluang untuk mencari magang atau beasiswa.",
        "body": [
            "Buka Peluang, lalu pakai kolom pencarian untuk mencari posisi, perusahaan, lokasi, atau kata kunci.",
            "Gunakan filter tipe, lokasi, dan urutan prioritas untuk mempersempit hasil yang paling relevan dengan profil.",
        ],
        "keywords": ["cari", "search", "peluang", "lowongan", "magang", "beasiswa", "filter"],
        "contexts": ["opportunities", "dashboard"],
        "roles": ["jobseeker", "admin"],
        "popular": True,
    },
    {
        "id": "bookmark-peluang",
        "title": "Cara bookmark peluang",
        "category": "Bookmark",
        "summary": "Simpan peluang agar mudah ditemukan lagi.",
        "body": [
            "Di halaman Peluang atau detail peluang, klik tombol bookmark untuk menyimpan peluang ke daftar Bookmark.",
            "Buka menu Bookmark untuk melihat peluang tersimpan. Dari sana, peluang bisa dihapus dari Bookmark atau ditambahkan ke tracker lamaran.",
        ],
        "keywords": ["bookmark", "simpan", "saved", "peluang", "favorit"],
        "contexts": ["opportunities", "dashboard"],
        "roles": ["jobseeker"],
        "popular": False,
    },
    {
        "id": "track-lamar-peluang",
        "title": "Cara track atau lamar peluang",
        "category": "Pelacakan Lamaran",
        "summary": "Tambahkan peluang ke tracker untuk memantau proses lamaran.",
        "body": [
            "Buka detail peluang, lalu pilih Track Lamaran atau Lamar Sekarang jika tombol tersedia.",
            "Pathora akan menambahkan peluang ke halaman Pelacakan Lamaran sehingga progresnya bisa dipantau di satu tempat.",
        ],
        "keywords": ["track", "lamar", "apply", "tracker", "peluang", "lamaran"],
        "contexts": ["opportunities", "applications", "dashboard"],
        "roles": ["jobseeker"],
        "popular": True,
    },
    {
        "id": "lihat-status-lamaran",
        "title": "Cara melihat status lamaran",
        "category": "Pelacakan Lamaran",
        "summary": "Pantau status review, interview, diterima, atau ditolak dari tracker.",
        "body": [
            "Buka Pelacakan Lamaran untuk melihat seluruh peluang yang sedang dipantau.",
            "Kolom Status menampilkan progres terbaru. Status dapat diperbarui oleh recruiter ketika pelamar sudah masuk proses review.",
        ],
        "keywords": ["status", "lamaran", "aplikasi", "review", "interview", "diterima", "ditolak"],
        "contexts": ["applications", "dashboard", "recruiter"],
        "roles": ["jobseeker", "recruiter"],
        "popular": True,
    },
    {
        "id": "pakai-chat",
        "title": "Cara memakai chat",
        "category": "Chat",
        "summary": "Gunakan Chat untuk mengirim pesan antara jobseeker dan recruiter.",
        "body": [
            "Buka Chat, pilih kontak atau percakapan, ketik pesan, lalu kirim.",
            "Jika tersedia, lampirkan gambar sesuai batas ukuran yang diterapkan aplikasi. Chat tetap berjalan tanpa AI assistant atau API eksternal.",
        ],
        "keywords": ["chat", "pesan", "message", "kontak", "gambar", "recruiter", "jobseeker"],
        "contexts": ["chat", "applications", "recruiter"],
        "roles": ["jobseeker", "recruiter"],
        "popular": True,
    },
    {
        "id": "recruiter-lihat-applicant",
        "title": "Recruiter melihat applicant",
        "category": "Recruiter",
        "summary": "Recruiter dapat membuka daftar pelamar dari menu Daftar Pelamar.",
        "body": [
            "Login sebagai recruiter, buka Daftar Pelamar, lalu gunakan daftar kandidat untuk melihat nama, peluang yang dilamar, skill match, dan status.",
            "Klik Lihat Detail untuk membuka profil pelamar, dokumen, ringkasan kecocokan, dan aksi lanjutan yang tersedia.",
        ],
        "keywords": ["recruiter", "applicant", "pelamar", "kandidat", "daftar pelamar", "skill match"],
        "contexts": ["recruiter"],
        "roles": ["recruiter", "admin"],
        "popular": True,
    },
    {
        "id": "recruiter-ubah-status",
        "title": "Recruiter mengubah status applicant",
        "category": "Recruiter",
        "summary": "Perbarui status lamaran dari halaman detail applicant.",
        "body": [
            "Buka Daftar Pelamar, pilih Lihat Detail pada applicant, lalu gunakan aksi status yang tersedia di bagian bawah detail.",
            "Status yang disimpan akan muncul di tracker jobseeker pada halaman Pelacakan Lamaran.",
        ],
        "keywords": ["recruiter", "status", "applicant", "pelamar", "diterima", "ditolak", "interview"],
        "contexts": ["recruiter", "applications"],
        "roles": ["recruiter", "admin"],
        "popular": True,
    },
    {
        "id": "admin-kelola-peluang",
        "title": "Admin mengelola peluang",
        "category": "Admin",
        "summary": "Admin dapat membuat, mengedit, dan menghapus peluang dari area Admin.",
        "body": [
            "Login sebagai admin, buka menu Admin, lalu masuk ke Kelola Peluang.",
            "Gunakan Tambah Peluang untuk membuat data baru, Edit untuk memperbarui detail, dan Hapus hanya ketika peluang memang tidak perlu ditampilkan lagi.",
        ],
        "keywords": ["admin", "kelola", "peluang", "create", "edit", "hapus"],
        "contexts": ["admin", "opportunities"],
        "roles": ["admin"],
        "popular": False,
    },
    {
        "id": "fitur-segera-hadir",
        "title": "Fitur yang belum aktif",
        "category": "Fitur Segera Hadir",
        "summary": "Beberapa tombol masih disiapkan dan belum menjalankan flow produksi.",
        "body": [
            "Google Login, LinkedIn Login, dan Lupa Password belum aktif. Untuk masuk, gunakan email dan password yang terdaftar.",
            "Video Call, Telepon, dan Jadwalkan Chat juga belum aktif. Gunakan Chat teks sebagai kanal komunikasi utama untuk saat ini.",
            "Pusat bantuan ini tidak membuat support ticket dan tidak memanggil AI/API eksternal.",
        ],
        "keywords": ["google", "linkedin", "lupa password", "video call", "telepon", "jadwalkan chat", "segera hadir"],
        "contexts": ["chat", "dashboard", "recruiter"],
        "roles": ["general"],
        "popular": True,
    },
]


def _copy_article(article):
    copied = article.copy()
    copied["body"] = list(article.get("body", []))
    copied["keywords"] = list(article.get("keywords", []))
    copied["contexts"] = list(article.get("contexts", []))
    copied["roles"] = list(article.get("roles", []))
    return copied


def _normalize(value):
    return (value or "").strip().lower()


def _article_haystack(article):
    searchable_parts = [
        article.get("title", ""),
        article.get("category", ""),
        article.get("summary", ""),
        " ".join(article.get("keywords", [])),
        " ".join(article.get("body", [])),
    ]
    return " ".join(searchable_parts).lower()


def _matches_query(article, query):
    query = _normalize(query)
    if not query:
        return True
    haystack = _article_haystack(article)
    return all(term in haystack for term in query.split())


def _matches_category(article, category):
    category = _normalize(category)
    if not category:
        return True
    return _normalize(article.get("category")) == category


def _score_article(article, query=None, context=None, role=None):
    score = 0
    context = _normalize(context)
    role = _normalize(role)
    query = _normalize(query)
    roles = {_normalize(item) for item in article.get("roles", [])}
    contexts = {_normalize(item) for item in article.get("contexts", [])}

    if context and context in contexts:
        score += 100
    if role and role in roles:
        score += 35
    elif "general" in roles:
        score += 12
    if article.get("popular"):
        score += 8
    if query:
        title = _normalize(article.get("title"))
        keywords = " ".join(article.get("keywords", [])).lower()
        if query in title:
            score += 25
        if query in keywords:
            score += 15
    return score


def get_help_articles():
    return [_copy_article(article) for article in HELP_ARTICLES]


def get_help_categories():
    return list(HELP_CATEGORIES)


def get_help_contexts():
    return HELP_CONTEXT_LABELS.copy()


def search_help_articles(query=None, category=None, context=None, role=None):
    scored_articles = []
    for index, article in enumerate(HELP_ARTICLES):
        if not _matches_category(article, category):
            continue
        if not _matches_query(article, query):
            continue

        scored_articles.append(
            (
                -_score_article(article, query=query, context=context, role=role),
                index,
                _copy_article(article),
            )
        )

    scored_articles.sort(key=lambda item: (item[0], item[1]))
    return [article for _, _, article in scored_articles]


def get_popular_articles(role=None):
    popular_articles = [article for article in HELP_ARTICLES if article.get("popular")]
    scored_articles = [
        (
            -_score_article(article, role=role),
            index,
            _copy_article(article),
        )
        for index, article in enumerate(popular_articles)
    ]
    scored_articles.sort(key=lambda item: (item[0], item[1]))
    return [article for _, _, article in scored_articles[:5]]
