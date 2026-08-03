# Smart Hydroponic MCP

Selamat datang di dokumentasi resmi **Smart Hydroponic MCP (Model Context Protocol)**!

Proyek ini menjembatani agen AI (LLM) dengan data sensor aktual dari sistem hidroponik Anda secara *real-time* dan efisien menggunakan TimescaleDB.

## Fitur Utama
- **Read-Only Data Retrieval**: Mengambil data sensor terbaru.
- **Optimasi Time-Series**: Memanfaatkan fungsionalitas `time_bucket` dari TimescaleDB untuk agregasi data.
- **FastMCP**: Dibangun di atas library `FastMCP` (berbasis FastAPI) untuk kemudahan akses via HTTP SSE/REST.
- **Keamanan Data**: Menggunakan pool koneksi `asyncpg` yang dijamin efisien dan terlindungi dari injeksi SQL.

Pilih menu di navigasi untuk melihat detail **Arsitektur** atau spesifikasi **API & Tools**.
