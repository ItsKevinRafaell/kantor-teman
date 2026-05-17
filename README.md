# GMaps Lead Gen

Aplikasi web untuk mencari bisnis lokal via Google Places API dan mengekstrak kontak WhatsApp.

## Struktur Folder

```
gmaps-lead-gen/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/app/
    │   ├── page.tsx
    │   ├── layout.tsx
    │   └── globals.css
    ├── package.json
    ├── tsconfig.json
    └── .env.local.example
```

## Cara Menjalankan

### 1. Backend (FastAPI)

```bash
cd backend

# Salin dan isi API key
cp .env.example .env
# Edit .env, isi GOOGLE_API_KEY dengan key dari Google Cloud Console

# Buat virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Jalankan server
uvicorn main:app --reload --port 8000
```

Backend berjalan di: http://localhost:8000  
Docs API: http://localhost:8000/docs

### 2. Frontend (Next.js)

```bash
cd frontend

# Salin env
cp .env.local.example .env.local

# Install dependencies
npm install

# Jalankan dev server
npm run dev
```

Frontend berjalan di: http://localhost:3000

## Setup Google Places API

1. Buka [Google Cloud Console](https://console.cloud.google.com)
2. Buat project baru atau pilih yang sudah ada
3. Aktifkan **Places API**
4. Buat API Key di **Credentials**
5. Isi key tersebut di `backend/.env`

## Catatan

- Setiap pencarian memanggil Places Text Search + Place Details per bisnis (untuk nomor telepon), sehingga mengonsumsi kuota API.
- Nomor telepon dikonversi otomatis ke format internasional Indonesia (`62xxx`) untuk link WhatsApp.
