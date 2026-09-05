# 🌱 Smart Hydroponic MCP Server

Server **Model Context Protocol (MCP)** berbasis semantic context untuk sistem IoT Smart Hydroponic. Menghubungkan Large Language Models (LLM) dengan database time-series **PostgreSQL + TimescaleDB** secara aman, efisien, dan terstandardisasi.

> **Apa itu Model Context Protocol (MCP)?**  
> MCP adalah standar terbuka (*open standard*) yang memungkinkan agen kecerdasan buatan (seperti Claude Desktop, Cursor, atau custom LLM agent) mengakses data real-time, context feeds, tools terparameterisasi, dan prompt workflow secara seragam tanpa membebani LLM dengan kueri SQL mentah.

---

## ✨ Fitur Utama

- **📦 MCP Resource (`hydroponic://state/latest`):** Menyajikan snapshot telemetri kondisi kebun terkini (pH, TDS, suhu rata-rata, kelembapan, flowrate, volume tandon, dan status aktuator) dalam format teks bersih untuk LLM.
- **📈 Downsampled Historical Trend (`get_historical_trend`):** Menggunakan fungsi TimescaleDB `time_bucket('1 hour', dataid)` untuk menyajikan tren historis teragregasi (rata-rata, minimum, maksimum, sampel) tanpa menghabiskan context window LLM.
- **⚡ Actuator Uptime Summary (`get_actuator_summary`):** Menghitung keandalan sistem dan persentase aktif aktuator (`pump_status`, `light_status`, `automation_status`) selama rentang waktu evaluasi.
- **🩺 Standardized Diagnostic Prompt (`diagnose_environment`):** Workflow prompt cerdas yang memandu AI membandingkan kondisi riil terhadap standar agronomi hidroponik dan menyusun diagnosis komprehensif.
- **🛡️ SQLAlchemy 2.0 Async Core & Safe Raw SQL:** Koneksi dikelola dengan `create_async_engine` dan `async_sessionmaker`, sementara query dieksekusi dengan parameterized binding `:param` yang kebal terhadap SQL Injection.
- **🧪 Automated Testing & CI/CD:** Dilengkapi test suite `pytest` dan pipeline GitHub Actions otomatis untuk linting, testing, dan Docker build/push.

---

## 📋 Prasyarat

- Python >= 3.14
- Package Manager: [`uv`](https://docs.astral.sh/uv/)
- PostgreSQL dengan ekstensi **TimescaleDB** (mendukung partisi hypertable berbasis `UUIDv7` / `timestamp`).

---

## ⚙️ Konfigurasi Environment

Salin atau buat file `.env` di direktori utama:

```ini
HYDROPONIC_DB_HOST=127.0.0.1
HYDROPONIC_DB_PORT=5432
HYDROPONIC_DB_USER=admin_iot_db
HYDROPONIC_DB_PASSWORD=your_password
HYDROPONIC_DB_NAME=iot_hydroponik
HYDROPONIC_DB_SCHEMA=public
HYDROPONIC_TABLE_NAME=hydroponic_data
```

Atau menggunakan connection string tunggal:
```ini
DATABASE_URL=postgresql+asyncpg://admin_iot_db:your_password@127.0.0.1:5432/iot_hydroponik
```

---

## 🚀 Menjalankan Server

Proyek ini menggunakan standardisasi package manager `uv`:

```bash
# Sinkronisasi dependensi dan jalankan server
uv run main.py
```

Server HTTP SSE FastMCP akan aktif pada `http://0.0.0.0:8000`.

Untuk menjalankan pengujian otomatis:
```bash
# Menjalankan unit & integration tests
uv run pytest -v

# Pengecekan linter & format kode
uv run ruff check .
uv run ruff format --check .
```

---

## 🤖 Integrasi dengan AI Client (Claude Desktop / Cursor)

Tambahkan konfigurasi berikut pada file pengaturan MCP klien Anda (misalnya `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "smart-hydroponic": {
      "command": "uv",
      "args": [
        "run",
        "c:/path/to/smart-hydroponic-mcp/main.py"
      ],
      "env": {
        "HYDROPONIC_DB_HOST": "127.0.0.1",
        "HYDROPONIC_DB_PORT": "5432",
        "HYDROPONIC_DB_USER": "admin_iot_db",
        "HYDROPONIC_DB_PASSWORD": "your_password",
        "HYDROPONIC_DB_NAME": "iot_hydroponik"
      }
    }
  }
}
```

---

## 🐳 Docker Deployment

Server ini dapat dijalankan dalam kontainer Docker:

```bash
# Build Docker image secara lokal
docker build -t smart-hydroponic-mcp:latest .

# Menjalankan kontainer dengan file environment
docker run -d --name smart-hydroponic-mcp -p 8000:8000 --env-file .env smart-hydroponic-mcp:latest
```

Atau menggunakan Docker Compose:
```bash
docker compose up -d
```
