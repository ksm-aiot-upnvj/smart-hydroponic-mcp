# 🗺️ Smart Hydroponic MCP Development Roadmap

Roadmap ini merangkum rencana dan ide pengembangan fungsionalitas **Model Context Protocol (MCP)** untuk Smart Hydroponic MCP Server. Tujuannya adalah menjadikan LLM (Agen AI) sebagai Asisten Cerdas yang dapat membaca data telemetri, menganalisis tren, mendiagnosis kondisi kebun, dan berkolaborasi dengan sistem otomasi kebun hidroponik.

> [!NOTE]
> **Batasan Tanggung Jawab Arsitektur:**
> Sesuai dengan spesifikasi arsitektur proyek, kontrol fisik perangkat keras (aktuasi pompa/lampu via MQTT/CoAP) ditangani oleh repositori/layanan terpisah. Tanggung jawab utama MCP Server ini adalah **database querying, data aggregation, TimescaleDB downsampling, diagnosis reasoning, dan exposing system state secara aman ke LLM tanpa raw SQL generation oleh LLM**.

---

## ✅ Phase 1: Telemetry State & Time-Series Analytics (Completed / Current Version)
Fokus pada kapabilitas membaca (Read) dan agregasi cerdas dengan memanfaatkan fitur analitik TimescaleDB dan FastMCP agar LLM tidak kelebihan muatan data (*token limit*).

- [x] **MCP Resource: Real-Time Telemetry Snapshot (`hydroponic://state/latest`)**
  - **Rincian:** Resource async yang mengambil rekaman terbaru dari tabel `hydroponic_data` dan menyajikannya dalam format string bersih (pH, TDS, suhu, kelembapan, flowrate, volume tandon, dan status boolean aktuator).
  - **Status:** Selesai diimplementasikan dengan SQLAlchemy 2.0 Async Engine & Raw SQL.
- [x] **Downsampled Historical Trend Tool (`get_historical_trend`)**
  - **Rincian:** Tool analitik berbasis TimescaleDB `time_bucket('1 hour', dataid)` dengan parameter tervalidasi Pydantic (`metric` dan `hours`).
  - **Fitur:** Menghasilkan rata-rata per jam, nilai minimum, maksimum, dan jumlah sampel untuk metrik yang dipilih (pH, TDS, suhu rata-rata, kelembapan rata-rata, flowrate, dll.).
- [x] **Actuator Reliability & Uptime Tool (`get_actuator_summary`)**
  - **Rincian:** Menghitung persentase uptime aktuator (`pump_status`, `light_status`, `automation_status`) selama rentang jam tertentu menggunakan agregasi SQL.
- [x] **Prompt Workflow: Environment Diagnosis (`diagnose_environment`)**
  - **Rincian:** Prompt terstandarisasi yang memandu LLM untuk membaca resource status terkini, membandingkan parameter sensor terhadap ambang batas ideal agronomi (pH 5.5-6.5, TDS 800-1200 ppm, suhu 20-28°C, kelembapan 50-70%), dan menghasilkan laporan diagnosis terstruktur.
- [x] **Safe Parameterized Raw SQL Engine:**
  - **Rincian:** Menggantikan eksekusi query rentan dengan SQLAlchemy 2.0 `text()` dan parameter binding (`:param`), serta whitelist Enum untuk identifier kolom.
- [x] **Automated Testing Suite (`pytest` & `pytest-asyncio`):**
  - **Rincian:** Test suite komprehensif menguji utilities, resource, prompt, tools, dan endpoint FastAPI yang terintegrasi dalam pipeline CI.

---

## 🚀 Phase 2: Advanced Anomaly Detection & System Health Metrics (Next Steps)
Memperluas kapabilitas analitik database untuk mendeteksi gangguan secara proaktif sebelum berdampak buruk pada tanaman.

- [ ] **Statistical Anomaly Detection Tool:**
  - `detect_sensor_anomalies(metric: str, hours_back: int, z_score_threshold: float = 2.5)`
  - **Rincian:** Menggunakan fungsi statistik TimescaleDB (`stddev`, `percentile_cont`, atau window functions) untuk mengidentifikasi lonjakan/penurunan drastis nilai sensor.
  - **Skenario:** LLM dapat langsung menyimpulkan: *"Terdeteksi lonjakan TDS mendadak sebesar +300 ppm pada pukul 14:00, kemungkinan dosis nutrisi terkonsentrasi berlebihan."*
- [ ] **Critical Condition Rule Checker (`check_critical_alerts`):**
  - **Rincian:** Kueri evaluasi kombinasi multi-sensor untuk mendeteksi *logical failures*:
    1. **Pump Dry Run / Pipe Leak:** `pump_status == TRUE` tetapi `flowrate == 0.0`.
    2. **Low Water Reservoir:** `distance_cm` mendekati batas bawah tandon.
    3. **Prolonged Nutrient Lockout:** `pH > 7.5` bertahan lebih dari 2 jam berturut-turut.
- [ ] **Sensor Heartbeat & Data Freshness (`get_sensor_health`):**
  - **Rincian:** Menghitung delta waktu antara waktu saat ini dengan timestamp UUIDv7 data terakhir untuk mendeteksi sensor/ESP32 offline atau putus koneksi WiFi.

---

## 🌿 Phase 3: Agronomy & Plant Intelligence
Menggabungkan data teknis sensor dengan basis pengetahuan botani dan agronomi berbagai komoditas hidroponik.

- [ ] **Crop Requirement Lookup Table (`get_crop_thresholds`):**
  - `get_crop_thresholds(crop_name: str)`
  - **Rincian:** Menyediakan lookup profil agronomi (Selada/Lettuce, Pakcoy, Bayam, Mint, Melon) yang mencakup target rentang TDS, pH ideal, toleransi suhu air, dan kebutuhan penyinaran (DLI - Daily Light Integral).
  - **Skenario:** LLM dapat melakukan komparasi kontekstual: *"Untuk varietas Selada Romaine di fase vegetatif, target TDS saat ini (1300 ppm) terlalu tinggi. Batas optimal adalah 800 - 1000 ppm."*
- [ ] **Nutrient Solution Dosing Recommendations (`recommend_nutrient_adjustment`):**
  - **Rincian:** Algoritma kalkulasi estimasi volume air baku atau larutan pekat AB Mix yang perlu ditambahkan ke tandon untuk mencapai target TDS/pH.

---

## 🔗 Phase 4: Integration with Actuation & Alerting Services (Read-to-Action Bridge)
Menghubungkan hasil analisis MCP dengan notifikasi dan pipeline orkestrasi kebun.

- [ ] **Autonomous Alert Dispatching:**
  - Menghubungkan prompt diagnosis berkala (via cron job / webhook) ke bot notifikasi (Telegram, WhatsApp, Discord) saat status kesehatan bernilai `CRITICAL`.
- [ ] **Actuation Plan Generation (Human-in-the-Loop):**
  - LLM menghasilkan saran aksi kontrol perangkat keras yang ditinjau oleh operator kebun sebelum dieksekusi oleh backend MQTT.

---

## 📷 Phase 5: Vision & Multi-Modal Crop Inspection (Experimental)
Integrasi kamera IoT (ESP32-CAM) untuk inspeksi visual tanaman.

- [ ] **Plant Leaf Health Inspection:**
  - `get_latest_plant_image()`
  - **Rincian:** Menyediakan URL atau data base64 gambar visual daun untuk dianalisis oleh Multi-Modal LLM guna mendeteksi klorosis, nekrosis, defisiensi nitrogen/besi, atau hama tanaman.
