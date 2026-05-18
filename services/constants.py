from zoneinfo import ZoneInfo


SQLITE_TIMEOUT_SECONDS = 10
JAKARTA_TZ = ZoneInfo("Asia/Jakarta")

APPLICATION_STATUS_APPLIED = "Sudah Daftar"
RECRUITER_APPLICATION_STATUSES = [
    APPLICATION_STATUS_APPLIED,
    "Sedang Direview",
    "Interview",
    "Diterima",
    "Ditolak",
]
APPLICATION_STATUSES = RECRUITER_APPLICATION_STATUSES
LEGACY_APPLICATION_STATUS_LABELS = {
    "Belum Daftar": APPLICATION_STATUS_APPLIED,
    "Dokumen Disiapkan": APPLICATION_STATUS_APPLIED,
    "Applied": APPLICATION_STATUS_APPLIED,
    "Seleksi Administrasi": "Sedang Direview",
    "Reviewed": "Sedang Direview",
    "Shortlisted": "Sedang Direview",
    "Accepted": "Diterima",
    "Rejected": "Ditolak",
}
APPLICATION_STATUS_BADGE_CLASSES = {
    APPLICATION_STATUS_APPLIED: "status-applied",
    "Sedang Direview": "status-review",
    "Interview": "status-interview",
    "Diterima": "status-accepted",
    "Ditolak": "status-rejected",
}
APPLICANT_SORT_RECENT = "recent"
APPLICANT_SORT_SKILL_MATCH = "skill_match"
APPLICANT_SORT_OPTIONS = {APPLICANT_SORT_RECENT, APPLICANT_SORT_SKILL_MATCH}

DOCUMENT_TYPES = [
    "CV",
    "Transkrip",
    "Sertifikat",
    "Motivation Letter",
    "Portofolio",
    "KTP/KTM",
]

GOOGLE_MODEL_DEFAULT = "gemma-4-26b-a4b-it"
GOOGLE_TIMEOUT_DEFAULT_SECONDS = 120
AI_ASSISTANT_MAX_MESSAGE_LENGTH = 1000
CHAT_MESSAGE_MAX_LENGTH = 2000
AI_ASSISTANT_GENERIC_ERROR = (
    "AI Assistant belum bisa memproses pertanyaan. Coba lagi nanti."
)
AI_ASSISTANT_SYSTEM_PROMPT = """
Kamu adalah AI Assistant untuk platform Pathora.
Pathora adalah platform internship, scholarship, dan career tracker untuk mahasiswa/jobseeker dan recruiter.
Jawab hanya seputar penggunaan Pathora:
- cara daftar
- cara login
- cara mencari peluang
- cara apply/lamar
- bookmark peluang
- pelacakan lamaran
- status lamaran
- kelola dokumen
- upload dokumen
- profile/edit profile
- chat antar user
- recruiter/jobseeker
- bantuan penggunaan platform

Gunakan Bahasa Indonesia yang jelas, singkat, ramah, dan profesional.
Jika pertanyaan di luar konteks Pathora, arahkan kembali ke bantuan penggunaan platform.
Jangan mengarang fitur yang tidak tersedia di Pathora.
Untuk daftar akun, arahkan user membuka halaman Daftar, memilih role Jobseeker atau Recruiter, mengisi form yang tersedia, lalu login setelah berhasil.
Jangan menyebut verifikasi email, OTP, login sosial, atau integrasi pihak ketiga kecuali user menanyakannya dan fitur itu jelas tersedia.
Jangan meminta password, OTP, API key, token, atau data sensitif pengguna.
""".strip()

VALID_ROLES = {"jobseeker", "recruiter", "admin"}
PUBLIC_REGISTER_ROLES = {"jobseeker", "recruiter"}
ROLE_LABELS = {
    "jobseeker": "Jobseeker",
    "recruiter": "Recruiter / HRD",
    "admin": "Admin",
}
RECRUITER_POSITION_OPTIONS = [
    "HRD",
    "Human Resources Staff",
    "HR Generalist",
    "HR Specialist",
    "Recruiter",
    "Technical Recruiter",
    "Talent Acquisition",
    "Talent Acquisition Specialist",
    "Recruitment Officer",
    "People Operations",
    "People Development",
    "Employer Branding",
    "Internship Coordinator",
    "Campus Hiring Officer",
    "Hiring Manager",
    "Company Representative",
    "Founder / Owner",
    "Manager",
    "Supervisor",
    "Other",
]

USER_PROFILE_COLUMN_DEFINITIONS = {
    "nickname": "TEXT DEFAULT ''",
    "phone": "TEXT DEFAULT ''",
    "birth_date": "TEXT DEFAULT ''",
    "gender": "TEXT DEFAULT ''",
    "domicile": "TEXT DEFAULT ''",
    "bio": "TEXT DEFAULT ''",
    "university": "TEXT DEFAULT ''",
    "faculty": "TEXT DEFAULT ''",
    "major": "TEXT DEFAULT ''",
    "degree": "TEXT DEFAULT ''",
    "semester": "TEXT DEFAULT ''",
    "gpa": "TEXT DEFAULT ''",
    "entry_year": "TEXT DEFAULT ''",
    "desired_positions": "TEXT DEFAULT ''",
    "preferred_program": "TEXT DEFAULT ''",
    "preferred_locations": "TEXT DEFAULT ''",
    "work_arrangement": "TEXT DEFAULT ''",
    "interests": "TEXT DEFAULT ''",
    "linkedin": "TEXT DEFAULT ''",
    "github": "TEXT DEFAULT ''",
    "portfolio_url": "TEXT DEFAULT ''",
    "avatar_path": "TEXT DEFAULT ''",
    "updated_at": "TEXT DEFAULT ''",
}

PROFILE_FORM_FIELDS = [
    "name",
    "email",
    "skills",
    "nickname",
    "phone",
    "birth_date",
    "gender",
    "domicile",
    "bio",
    "university",
    "faculty",
    "major",
    "degree",
    "semester",
    "gpa",
    "entry_year",
    "desired_positions",
    "preferred_program",
    "preferred_locations",
    "work_arrangement",
    "interests",
    "linkedin",
    "github",
    "portfolio_url",
]

PROFILE_COMPLETION_FIELDS = [
    "name",
    "email",
    "skills",
    "university",
    "major",
    "degree",
    "gpa",
    "desired_positions",
    "preferred_program",
    "interests",
    "linkedin",
    "portfolio_url",
]
