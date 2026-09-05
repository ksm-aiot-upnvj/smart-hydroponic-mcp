# Smart Hydroponic MCP

Selamat datang di dokumentasi resmi **Smart Hydroponic MCP (Model Context Protocol)**!

Proyek ini menjembatani Agen Kecerdasan Buatan (LLM seperti Claude Desktop, Cursor, OpenAI Agents) dengan data telemetri aktual dari sistem hidroponik secara *real-time* dan efisien menggunakan TimescaleDB dan SQLAlchemy 2.0 Async Engine.

---

## 🌟 Fitur Unggulan

- **Context-Rich MCP Resource (`hydroponic://state/latest`)**: Menyediakan snapshot kondisi terkini kebun (pH, TDS, suhu, kelembapan, status pompa & lampu) dalam format teks bersih untuk LLM.
- **Downsampled Time-Series Analysis (`get_historical_trend`)**: Agregasi time-series otomatis dengan TimescaleDB `time_bucket` per jam agar LLM dapat menganalisis tren tanpa membebani context window.
- **Actuator Reliability Evaluation (`get_actuator_summary`)**: Menghitung persentase uptime dan durasi aktif pompa/aktuator untuk evaluasi keandalan kebun.
- **Automated Diagnostic Prompt (`diagnose_environment`)**: Workflow terstandarisasi untuk memandu AI mendiagnosis parameter lingkungan terhadap ambang batas agronomi ideal.
- **Arsitektur Cepat & Aman**: Menggunakan SQLAlchemy 2.0 Async Core dengan parameterized raw SQL (`:param`), immune terhadap SQL Injection.
- **Standardisasi Ekosistem**: Dikelola penuh menggunakan `uv`, dilengkapi test suite `pytest` otomatis dan CI/CD pipeline.

---

## 🧭 Navigasi Dokumentasi

- **[Arsitektur & Alur](architecture.md)**: Memahami diagram alur, interaksi agen AI, dan pemisahan batas tanggung jawab sistem.
- **[API, Resources & Tools](api.md)**: Spesifikasi lengkap parameter, output, dan contoh payload MCP Tools dan Resources.
