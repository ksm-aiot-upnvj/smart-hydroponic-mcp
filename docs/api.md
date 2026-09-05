# API, Resources & Tools Reference

Smart Hydroponic MCP Server mengekspos endpoint Model Context Protocol (MCP) dan HTTP standar yang siap diakses oleh Agen AI (seperti Claude Desktop, Cursor, OpenAI Agents) dan sistem eksternal.

---

## 📦 MCP Resources

Resources menyediakan data kontekstual yang dapat dibaca (*read-only*) oleh LLM tanpa memerlukan pemanggilan tool manual.

### `hydroponic://state/latest`
Mengambil baris telemetri sensor paling mutakhir dari tabel `hydroponic_data` dan mengonversinya menjadi string terstruktur yang rapi, padat, dan mudah dipahami oleh LLM.

- **URI:** `hydroponic://state/latest`
- **Output:** Ringkasan multi-kategori mencakup:
  - **Kualitas Air & Nutrisi:** Nilai pH aktual vs ambang batas ideal (5.5 - 6.5), TDS (ppm) vs batas (800 - 1200 ppm), Flowrate (L/min), Total Air (Liter), Jarak Permukaan Air (cm).
  - **Kondisi Lingkungan (Iklim Mikro):** Suhu rata-rata (°C), Suhu atas & bawah, Kelembapan rata-rata (%), Kelembapan atas & bawah, serta Kelembapan media tanam (Moisture).
  - **Status Aktuator:** Status Pompa Sirkulasi (ON/OFF), Grow Light (ON/OFF), dan Mode Otomasi (AUTO/MANUAL).

---

## 🛠️ MCP Tools

Tools adalah fungsi terparameterisasi dengan validasi tipe data Pydantic ketat yang dapat dipanggil secara dinamis oleh LLM.

### 1. `get_historical_trend` (Downsampled Time-Series)
Alat analitik utama untuk mengekstrak tren metrik tertentu selama rentang waktu historis tanpa membebani context window LLM. Menggunakan fungsi TimescaleDB `time_bucket` per jam.

- **Parameter:**
  - `metric` (*MetricType Enum, Wajib*): Pilihan metrik yang ingin dianalisis:
    - `"ph"`, `"tds"`, `"temperature_avg"`, `"humidity_avg"`, `"moisture_avg"`, `"flowrate"`, `"total_litres"`, `"distance_cm"`.
  - `hours` (*Integer, Default: 24, Batas: 1 - 168*): Jendela waktu dalam hitungan jam ke belakang.
- **Output:** List baris agregasi per jam berisi:
  - `timestamp`: Waktu awal bucket (format `YYYY-MM-DD HH:MM:SS`).
  - `metric`: Nama metrik yang diminta.
  - `average`: Rata-rata nilai dalam interval 1 jam.
  - `min`: Nilai terendah dalam interval.
  - `max`: Nilai tertinggi dalam interval.
  - `samples`: Jumlah datapoint sensor yang terkumpul dalam interval tersebut.

### 2. `get_actuator_summary` (Evaluasi Keandalan & Uptime)
Menghitung persentase keaktifan (*uptime percentage*) aktuator dan jumlah sampel aktif dalam rentang waktu yang ditentukan.

- **Parameter:**
  - `actuator` (*ActuatorType Enum, Wajib*):
    - `"pump_status"`, `"light_status"`, atau `"automation_status"`.
  - `hours` (*Integer, Default: 24, Batas: 1 - 168*): Rentang waktu jam evaluasi.
- **Output:**
  - `actuator`: Nama aktuator.
  - `window_hours`: Rentang evaluasi (jam).
  - `since_utc`: Waktu awal evaluasi.
  - `total_samples`: Total rekaman data dalam jendela waktu.
  - `active_samples`: Jumlah rekaman dengan status aktif (`TRUE`).
  - `uptime_percentage`: Persentase keaktifan (0.0% - 100.0%).
  - `status`: `"NORMAL"` atau `"NO_DATA"`.

### 3. `get_latest_sensor_data`
Mengambil 1 baris rekaman sensor terbaru dalam format JSON dictionary murni. Berguna untuk integrasi terprogram atau sistem visualisasi yang membutuhkan pasangan key-value mentah.

### 4. `get_sensor_data_summary`
Tool analitik multi-metrik yang mengelompokkan data berdasarkan interval waktu kustom (`bucket_width`, contoh: `"1 day"`, `"12 hours"`, `"1 hour"`).

- **Parameter:**
  - `num_buckets` (*Integer, Default: 7, Max: 14*): Jumlah interval bucket.
  - `bucket_width` (*String, Default: `"1 day"`*): Lebar interval bucket waktu.

### 5. `list_database_tables` & `describe_database_table`
Tool inspeksi metadata skema database untuk melihat tabel dan struktur kolom yang tersedia.

---

## 📝 MCP Prompts

### `diagnose_environment`
Workflow prompt terstandarisasi yang memandu Agen AI untuk melakukan diagnosis komprehensif terhadap kondisi kebun hidroponik.

- **Fungsi:** Menginstruksikan AI untuk:
  1. Membaca resource `hydroponic://state/latest`.
  2. Menganalisis parameter terhadap ambang batas agronomi (pH 5.5-6.5, TDS 800-1200 ppm, Suhu 20-28°C, Kelembapan 50-70%, integritas aliran pompa).
  3. Memanggil tool `get_historical_trend` atau `get_actuator_summary` jika ada anomali yang mencurigakan.
  4. Menghasilkan laporan diagnosis terstruktur dengan format:
     - **STATUS KESEHATAN SISTEM:** [HEALTHY / WARNING / CRITICAL]
     - **RINGKASAN KONDISI**
     - **ANALISIS PARAMETER**
     - **POTENSI RISIKO**
     - **REKOMENDASI TINDAKAN CEPAT**

---

## 🌐 HTTP REST Endpoints

| Endpoint | Method | Deskripsi |
| :--- | :--- | :--- |
| `/` | `GET` | Menampilkan metadata server, versi aplikasi, status operasional, dan info engine database. |
| `/health` | `GET` | Healthcheck endpoint untuk verifikasi kesiapan kontainer Docker / Kubernetes. |
| `/sse` | `GET` | Server-Sent Events (SSE) stream endpoint untuk koneksi MCP client. |
