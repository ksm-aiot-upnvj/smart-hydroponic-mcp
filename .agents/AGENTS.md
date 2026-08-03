# Aturan Agen (Project-Scoped Rules) untuk Smart Hydroponic MCP

Berikut adalah aturan dan panduan utama yang harus selalu diikuti saat bekerja pada repository ini:

## 1. Manajemen Dependency (Wajib `uv`)
- Proyek ini menggunakan `uv` sebagai package manager dan standardisasi environment Python.
- **Dilarang** menggunakan `pip install` standar secara langsung.
- Jika ada library/requirement tambahan yang dibutuhkan:
  - Gunakan `uv add <nama_package>` untuk menambahkan ke `pyproject.toml`.
  - Selalu jalankan sinkronisasi dengan `uv sync` untuk memastikan `.venv` dan `uv.lock` ter-update.

## 2. Fitur Spesifik Database (TimescaleDB & UUIDv7)
- Proyek ini menggunakan arsitektur TimescaleDB dan mengandalkan **UUIDv7** sebagai Primary Key sekaligus untuk tracking *timestamp*.
- Jika Anda (agent) tidak mengingat atau tidak mengetahui sintaks terbaru dari TimescaleDB (misalnya: dukungan native UUIDv7 untuk fungsi `time_bucket`), **WAJIB** menggunakan tool search web/dokumentasi (seperti `search_web`) untuk memverifikasi sintaks yang benar sebelum menulis/memperbarui query SQL. Dilarang berasumsi jika tidak yakin.

## 3. Best Practices Umum & Clean Code
- **Keamanan (Anti SQL Injection):** Selalu gunakan *parameterized binding* (misal `$1`, `$2` di `asyncpg`) dan jangan pernah menggabungkan (*concatenate*) input pengguna langsung ke dalam string query SQL.
- **DRY (Don't Repeat Yourself):** Ekstrak logika kode yang berulang menjadi fungsi *helper* tersendiri.
- **Asynchronous Programming:** Pastikan fungsi yang berurusan dengan I/O (Database, Network) menggunakan `async`/`await` secara konsisten.
- **Manajemen Koneksi:** Selalu tangani koneksi pool database dengan hati-hati (disarankan menggunakan *Lifespan events* dari framework HTTP saat inisialisasi).
- **Type Hinting:** Gunakan Python type hinting (e.g., `-> list[dict[str, Any]]`) pada semua deklarasi tool dan fungsi.
