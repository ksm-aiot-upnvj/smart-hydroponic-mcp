#  Smart Hydroponic MCP Development Roadmap

Roadmap ini merangkum rencana dan ide pengembangan fungsionalitas **Model Context Protocol (MCP)** untuk Smart Hydroponic MCP Server. Tujuannya adalah menjadikan LLM (Agen AI) sebagai Asisten Cerdas yang tidak hanya bisa membaca data, tetapi juga menganalisis, mendiagnosis, dan bahkan mengontrol sistem (Autonomous / Semi-Autonomous Agent).

---

##  Phase 1: Advanced Analytics & Time-Series Mastery
Fokus pada memperluas kapabilitas baca (Read) dengan memanfaatkan fitur-fitur analitik lanjutan dari TimescaleDB agar LLM tidak kelebihan muatan data (*token limit*).

- [ ] **Custom Time-Range Query Tool:**
  - `query_sensor_data_by_time(start_time, end_time, interval)`
  - **Rincian:** Tool ini memungkinkan LLM memotong data berdasarkan waktu spesifik dengan interval agregasi (misal: rata-rata per jam). 
  - **Skenario:** Jika Anda menyadari tanaman layu pagi ini, LLM bisa menanyakan data historis spesifik: *"Tolong ekstrak data suhu dan kelembapan kemarin antara jam 12:00 siang hingga 15:00 sore."*
- [ ] **Anomaly Detection Tool:**
  - `detect_anomalies(hours_back)`
  - **Rincian:** Sebuah query TimescaleDB yang menggunakan fungsi statistik (`stddev`, `percentile_cont`) untuk mencari fluktuasi anomali.
  - **Skenario:** LLM tidak perlu melihat ribuan baris data. Tool ini langsung menyajikan kesimpulan database: *"Ditemukan 2 anomali: Lonjakan suhu ekstrim (naik 5°C dalam 30 menit) pada pukul 14:00, dan TDS drop mendadak pada pukul 15:30."*
- [ ] **Database & System Statistics:**
  - `get_system_stats()`
  - **Rincian:** Menampilkan metadata seperti jumlah record total, tanggal data pertama, dan tanggal data terakhir. Membantu LLM memahami konteks usia sistem.

---

##  Phase 2: Action & Control (Actuation)
Mengubah peran LLM dari sekadar 'Pemantau' menjadi 'Pengendali' (Write Operations) yang terhubung ke sistem keras IoT.

- [ ] **Hardware Control Tools:**
  - `set_pump_status(state: bool)` / `set_grow_light(state: bool, brightness: int)`
  - **Rincian:** Endpoint MCP ini akan mengirimkan *payload* eksekusi ke message broker (MQTT) atau REST API lokal yang didengarkan oleh ESP32/Raspberry Pi.
  - **Skenario:** LLM menyadari suhu air terlalu panas, lalu mengambil inisiatif: *"Suhu air 30°C. Saya telah menghidupkan pompa sirkulasi cadangan untuk mendinginkan tandon."*
- [ ] **Automation Configuration Updates:**
  - `update_target_thresholds(target_ph, target_tds)`
  - **Rincian:** Mengubah parameter *target* otomasi di dalam tabel `system_config`.
  - **Skenario:** Ketika usia tanaman bertambah 1 minggu, LLM merekomendasikan dan langsung mengeksekusi penambahan nutrisi: *"Sesuai jadwal minggu ke-3, saya telah mengubah target batas bawah TDS sistem Anda dari 800 ke 1000 ppm."*
- [ ] **Human-in-the-Loop (HitL) Security:**
  - **Rincian:** Demi keamanan kebun, *Write Tools* yang dieksekusi LLM harus memiliki mekanisme konfirmasi (misalnya membutuhkan kata sandi otorisasi atau mencetak log persetujuan) sebelum aktuator benar-benar dinyalakan, mencegah malfungsi (seperti pompa menyala terus menerus).

---

##  Phase 3: Agronomy & Plant Intelligence
Menggabungkan data teknis sensor dengan pengetahuan biologi pertanian.

- [ ] **Crop Requirement Knowledge Base:**
  - `get_crop_requirements(crop_name: str)`
  - **Rincian:** Menyediakan *lookup table* internal (JSON atau tabel statis) yang berisi batas ideal Suhu, TDS, pH, Kelembapan untuk berbagai tanaman (Selada, Pakcoy, Kangkung, dll).
  - **Skenario:** LLM bisa membandingkan secara otomatis: *"Anda sedang menanam Selada. Batas aman pH Selada adalah 5.5 - 6.5. Namun sensor menunjukkan pH 7.2 saat ini, Anda berisiko mengalami 'Nutrient Lockout' (akar gagal menyerap nutrisi)."*

---

##  Phase 4: Diagnostic & Proactive Alerting (Sistem Peringatan Dini)
Di fase ini, kita mengubah LLM dari sekadar alat penjawab pertanyaan menjadi sistem detektif cerdas yang menyimpulkan "kesehatan sistem" secara holistik.

- [ ] **System Health Check Tool (`check_critical_alerts`)**
  - **Rincian:** Tool ini mengeksekusi kueri kombinasi dari beberapa tabel dan kolom sekaligus untuk mencari *logical errors* (kondisi berbahaya). Aturan-aturan ini (hard rules) ditanamkan di SQL atau logic Python.
  - **Contoh Aturan (Rules):**
    1. **Water Leakage/Pump Failure:** Jika `flowrate == 0` padahal `pump_status == ON`. (Pompa nyala tapi air tidak mengalir).
    2. **Empty Reservoir:** Jika nilai `distance_cm` (sensor ultrasonik tandon) sangat besar mendekati dasar tandon.
    3. **Nutrient Lockout:** Jika `pH > 7.5` bertahan lebih dari 1 jam tanpa turun meskipun pompa menyala.
  - **Skenario:** Anda mengatur *cron job* untuk menyuruh agen LLM berjalan setiap jam. LLM memanggil tool ini dan langsung mengirim notifikasi WhatsApp/Telegram: *" DARURAT: Pompa A berstatus ON, tetapi aliran air (flowrate) 0 liter/menit. Segera periksa kebun! Ada kemungkinan pipa utama lepas/bocor, atau pompa rusak/terbakar!"*
- [ ] **IoT Device Status Tool (`get_sensor_status`)**
  - **Rincian:** Tool yang mengevaluasi jarak waktu (*delta time*) antara waktu sekarang (Now) dengan *timestamp* UUIDv7 data terakhir yang masuk ke tabel `hydroponic_data`.
  - **Skenario:** Jika jaraknya lebih dari 15 menit, artinya modul ESP32/Sensor Anda mati lampu atau putus koneksi WiFi. LLM akan langsung melaporkan: *"Sistem tidak dapat dianalisis. Saya mendeteksi hilangnya koneksi sensor sejak 15 menit yang lalu. Harap pastikan kebun Anda tidak mati listrik."*

---

##  Phase 5: Vision & Multi-Modal (Eksperimental)
Menggabungkan kemampuan *vision* (penglihatan) LLM modern ke dalam hidroponik.

- [ ] **Plant Vision Inspection & Disease Detection:**
  - **Rincian:** Mengintegrasikan kamera (seperti ESP32-CAM) yang diunggah secara reguler untuk mendeteksi penyakit atau kondisi fisik tanaman dari gambar. Terdapat dua pendekatan yang bisa diimplementasikan:
    1. **Deep Learning (Klasifikasi) + LLM (Deskripsi & Rekomendasi)**
       - Model Deep Learning berbasis CNN bertugas melakukan klasifikasi penyakit/kondisi tanaman secara cepat.
       - LLM bertugas memberikan deskripsi detail dan rekomendasi penanganan berdasarkan hasil klasifikasi CNN.
    2. **LLM-Only (Klasifikasi, Deskripsi & Rekomendasi Langsung)**
       - LLM dengan kemampuan Multi-Modal secara langsung memproses gambar untuk klasifikasi, deskripsi, dan rekomendasi.
       - *Catatan:* Karena domain LLM terlalu luas, pendekatan ini mengharuskan LLM dibuat lebih spesifik melalui **RAG (Retrieval-Augmented Generation)** atau **Fine-Tuning** agar analisisnya akurat dan *on-point*.
  - `get_latest_plant_image_url()`
  - **Skenario:** Analisis gambar daun menunjukkan: *"Berdasarkan data TDS yang tinggi, dan terlihat pada foto ada bercak terbakar di ujung daun (tip burn), ini mengonfirmasi bahwa dosis nutrisi Anda terlalu pekat. Segera tambahkan air baku ke tandon."*
