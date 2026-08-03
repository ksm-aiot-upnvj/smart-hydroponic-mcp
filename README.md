# Smart Hydroponic MCP Server

Proyek ini adalah sebuah **Model Context Protocol (MCP) Server** yang dikhususkan untuk berinteraksi dengan database sensor hidroponik (menggunakan PostgreSQL + TimescaleDB). 

> **Apa itu MCP?**  
> **Model Context Protocol (MCP)** adalah standar terbuka (*open standard*) yang memungkinkan asisten AI (seperti Claude) untuk terhubung secara aman dengan sumber data, *tools*, dan *prompt* eksternal. Melalui MCP, LLM dapat berinteraksi dengan sistem dan data lokal Anda menggunakan arsitektur client-server yang seragam.

Server ini mengekspos tools yang bisa digunakan oleh LLM (seperti Claude Desktop) untuk membaca data sensor terbaru dan melakukan agregasi secara dinamis.

## Prasyarat

- Python >= 3.14
- `uv` Package Manager
- PostgreSQL dengan ekstensi **TimescaleDB** (termasuk dukungan untuk fitur native `UUIDv7` pada fungsi `time_bucket`).

## Environment Variables

Salin file (atau buat) `.env` di *root directory* dan pastikan variabel-variabel berikut telah disetel:

```ini
HYDROPONIC_DB_HOST=127.0.0.1
HYDROPONIC_DB_PORT=5432
HYDROPONIC_DB_USER=your_db_user
HYDROPONIC_DB_PASSWORD=your_db_password
HYDROPONIC_DB_NAME=your_db_name
HYDROPONIC_DB_SCHEMA=public
HYDROPONIC_TABLE_NAME=hydroponic_data
```

## Instalasi & Menjalankan Server

Proyek ini sepenuhnya mengelola dependencies melalui `uv`. Anda tidak perlu menggunakan `pip install` secara manual.

Untuk menjalankan server HTTP / FastMCP secara lokal, cukup gunakan:

```bash
uv run main.py
```

Perintah di atas akan secara otomatis memvalidasi environment (memastikan `uv.lock` sinkron), membuat `.venv`, dan menyalakan server uvicorn pada `http://0.0.0.0:8000`.

## Integrasi dengan LLM Client (Contoh: Claude Desktop)

Untuk menyambungkan server ini ke aplikasi yang mendukung Model Context Protocol (seperti Claude Desktop), tambahkan konfigurasi berikut pada file pengaturan klien (contohnya `claude_desktop_config.json`):

**Via UV Stdio (Disarankan untuk environment lokal yang aman):**
```json
{
  "mcpServers": {
    "smart-hydroponic": {
      "command": "uv",
      "args": [
        "run",
        "c:/path/to/your/project/smart-hydroponic-mcp/main.py"
      ],
      "env": {
        "HYDROPONIC_DB_USER": "your_db_user",
        "HYDROPONIC_DB_PASSWORD": "your_db_password",
        "HYDROPONIC_DB_NAME": "your_db_name",
        "HYDROPONIC_DB_HOST": "127.0.0.1",
        "HYDROPONIC_DB_PORT": "5432"
      }
    }
  }
}
```

*Catatan: Pastikan Anda menyesuaikan path dan kredensial dengan environment mesin Anda.*

## Fitur (MCP Tools)

- `list_database_tables()`: Menampilkan semua tabel yang ada dalam skema database.
- `describe_database_table(table_name)`: Mendeskripsikan tipe data dan struktur dari sebuah tabel.
- `read_hydroponic_table(limit)`: Membaca baris-baris data hidroponik terbaru (bisa diatur batas limitnya).
- `get_latest_sensor_data()`: Mengambil 1 entri sensor paling terakhir secara spesifik (cocok untuk dashboard real-time).
- `get_sensor_data_summary(num_buckets, bucket_width)`: Agregasi time-series cerdas. LLM dapat menanyakan "Bagaimana rata-rata pH 7 hari terakhir?", dan tool ini akan memanfaatkan fitur `time_bucket` dari TimescaleDB untuk langsung memberikan jawabannya secara efisien.
