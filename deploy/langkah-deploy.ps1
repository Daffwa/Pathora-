# Deploy Pathora ke Railway

## 1. Push ke GitHub
Buka https://github.com, buat repo baru (public/private), lalu jalankan:

```powershell
cd D:\Matkul baru\Perancangan Aplikasi Sains Data\Project website rev 2 v2\Project website rev 2 v1\Project website
git remote add origin https://github.com/NAMA_USER/NAMA_REPO.git
git branch -M main
git push -u origin main
```

## 2. Deploy ke Railway
1. Buka https://railway.app → Login with GitHub
2. New Project → Deploy from GitHub → pilih repo tadi
3. Build & deploy otomatis (tunggu 1-2 menit)

## 3. Setup Volume & Variables
Di dashboard Railway service Pathora:

- **Variables** → tambah:
  - `DATA_DIR` = `/app/data`
  - `SECRET_KEY` = (isi string acak panjang, misal pake: `python -c "import secrets; print(secrets.token_hex(32))"`)
  - `ADMIN_PASSWORD` = (isi password admin yang kuat, jangan pakai `admin12345`)
  - `GOOGLE_API_KEY` = (isi API key Google kamu)
  - `GOOGLE_MODEL` = `gemma-4-26b-a4b-it`
  - `GOOGLE_TIMEOUT_SECONDS` = `120`
  - `USE_BUILT_ASSETS` = `true`

- **Volumes** → Add Volume:
  - Mount path: `/app/data`
  - Size: 1 GB (free tier)

- **Settings** → Generate Domain → dapat URL public

## 4. Selesai
Pathora online di `https://namaproject.railway.app`
