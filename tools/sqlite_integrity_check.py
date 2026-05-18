import argparse
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "database" / "app.db"
BACKUP_ROOT = PROJECT_ROOT / "database" / "integrity_check_backups"


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Run PRAGMA integrity_check safely on a copied SQLite database. "
            "The original database is never overwritten."
        )
    )
    parser.add_argument(
        "--database",
        default=str(DATABASE_PATH),
        help="Path to the SQLite database. Defaults to database/app.db.",
    )
    parser.add_argument(
        "--work-dir",
        default=str(BACKUP_ROOT),
        help="Folder for timestamped database copies used by this check.",
    )
    return parser


def copy_database_files(database_path, work_dir):
    if not database_path.exists():
        raise FileNotFoundError(f"Database file tidak ditemukan: {database_path}")
    if not database_path.is_file():
        raise RuntimeError(f"Path database bukan file: {database_path}")

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    check_dir = work_dir / f"integrity_check_{timestamp}"
    check_dir.mkdir(parents=True, exist_ok=False)

    copied_database = check_dir / database_path.name
    shutil.copy2(database_path, copied_database)

    journal_path = database_path.with_name(f"{database_path.name}-journal")
    copied_journal = None
    if journal_path.exists():
        copied_journal = check_dir / journal_path.name
        shutil.copy2(journal_path, copied_journal)

    return copied_database, copied_journal, check_dir


def run_integrity_check(database_path):
    with sqlite3.connect(str(database_path), timeout=10) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return [
            row[0]
            for row in connection.execute("PRAGMA integrity_check;").fetchall()
        ]


def run_database_only_fallback(original_database_path, check_dir):
    fallback_dir = check_dir / "without_journal"
    fallback_dir.mkdir(parents=True, exist_ok=False)
    fallback_database = fallback_dir / original_database_path.name
    shutil.copy2(original_database_path, fallback_database)

    print()
    print("Fallback aman: menjalankan integrity_check pada salinan app.db tanpa journal.")
    print(f"Salinan tanpa journal: {fallback_database}")
    try:
        results = run_integrity_check(fallback_database)
    except sqlite3.Error as exc:
        print(f"Fallback tanpa journal juga gagal: {exc}")
        return None

    print("Hasil fallback tanpa journal:")
    for result in results:
        print(result)

    if results == ["ok"]:
        print(
            "Catatan: file app.db utama lolos saat journal diabaikan. "
            "Masalah kemungkinan ada pada hot journal, proses SQLite yang masih aktif, "
            "atau recovery journal yang gagal. Tetap backup app.db dan app.db-journal "
            "sebelum tindakan manual."
        )
    return results


def print_recovery_steps(original_database_path):
    backup_dir = original_database_path.parent / (
        "manual_backup_before_recovery_YYYYMMDDHHMMSS"
    )
    recovered_database_path = original_database_path.with_name("app.recovered.db")
    print()
    print("Jika hasil integrity_check bukan 'ok' atau proses gagal:")
    print("1. Stop server Flask/Python yang sedang memakai database.")
    print(f"2. Buat backup folder baru, contoh: {backup_dir}")
    print(f"3. Copy file lama ke backup: {original_database_path}")
    print(
        f"4. Jika ada, copy juga journal: "
        f"{original_database_path.with_name(original_database_path.name + '-journal')}"
    )
    print("5. Dump database lama jika masih bisa dibaca.")
    print(f"6. Restore dump ke file baru: {recovered_database_path}")
    print("7. Verifikasi file baru dengan PRAGMA integrity_check;")
    print("8. Ganti database aplikasi hanya setelah backup dan verifikasi berhasil.")
    print("Jangan overwrite app.db lama sebelum backup dibuat.")


def main():
    args = build_parser().parse_args()
    original_database = Path(args.database).expanduser().resolve()
    work_dir = Path(args.work_dir).expanduser().resolve()

    print(f"Database asli: {original_database}")
    print(f"Folder kerja aman: {work_dir}")

    copied_database, copied_journal, check_dir = copy_database_files(
        original_database, work_dir
    )
    print(f"Salinan database: {copied_database}")
    if copied_journal is not None:
        print(f"Salinan journal: {copied_journal}")
    else:
        print("File journal tidak ditemukan.")

    try:
        results = run_integrity_check(copied_database)
    except sqlite3.Error as exc:
        print(f"PRAGMA integrity_check gagal dijalankan: {exc}")
        run_database_only_fallback(original_database, check_dir)
        print_recovery_steps(original_database)
        raise SystemExit(2) from exc

    print("Hasil PRAGMA integrity_check:")
    for result in results:
        print(result)

    if results == ["ok"]:
        print("Status: database copy lolos integrity_check.")
    else:
        print("Status: database copy terindikasi bermasalah.")
        print_recovery_steps(original_database)


if __name__ == "__main__":
    main()
