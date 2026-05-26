# Access Control Pathora

Pathora memakai RBAC sebagai kontrol akses utama, dengan ownership check untuk
data personal dan data milik recruiter.

## Role dan permission

| Role | Permission utama |
| --- | --- |
| `jobseeker` | Akses dashboard jobseeker, melihat peluang, bookmark sendiri, lamaran sendiri, dokumen sendiri, profil sendiri, chat, AI Assistant |
| `recruiter` | Akses dashboard recruiter, melihat peluang, mengelola lowongan sendiri, mengelola applicant pada lowongan sendiri, chat, AI Assistant |
| `admin` | Akses dashboard admin, mengelola seluruh lowongan, mengelola semua applicant, mengecek health AI, mengelola status akun recruiter |

Matrix permission teknis ada di `services/constants.py` pada
`ROLE_PERMISSION_MATRIX`. Route guard membaca permission melalui
`services/auth_service.py`, lalu role dan status akun disegarkan ulang dari
database sebelum akses diberikan.

## Status akun recruiter

Recruiter dan jobseeker baru langsung dibuat dengan
`account_status = 'approved'`, sehingga user bisa langsung memakai fitur sesuai
role-nya setelah register. Admin tetap bisa mengubah status recruiter lewat
halaman `/admin/recruiters` jika diperlukan untuk moderasi akun.

Status yang tersedia:

| Status | Arti |
| --- | --- |
| `pending` | Recruiter ditahan sementara oleh admin |
| `approved` | Recruiter aktif dan bisa memakai fitur recruiter |
| `rejected` | Recruiter ditolak dan tidak bisa memakai fitur recruiter |

## Ownership check

Selain role, query penting tetap memfilter pemilik data:

| Data | Pembatas |
| --- | --- |
| Dokumen | `documents.user_id = session["user_id"]` |
| Lamaran jobseeker | `applications.user_id = session["user_id"]` |
| Lowongan recruiter | `opportunities.created_by = session["user_id"]` |
| Applicant recruiter | Applicant hanya muncul jika opportunity dibuat recruiter tersebut |
| Chat attachment | File hanya dikirim jika user adalah participant thread |

## Audit log

Tabel `audit_logs` mencatat aksi penting seperti login, pendaftaran akun,
perubahan status recruiter, upload dokumen, create/update/delete lowongan, dan
update status applicant.
