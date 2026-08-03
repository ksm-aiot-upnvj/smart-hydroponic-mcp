# API & MCP Tools

Semua fungsionalitas ini terdaftar otomatis dan dapat dieksekusi oleh Agen LLM yang terhubung via Model Context Protocol.

## 1. list_database_tables
Mengembalikan daftar (*list*) semua nama tabel yang berada dalam skema yang dikonfigurasi (default: `public`). Sangat berguna untuk membantu agen melihat struktur database awal.

## 2. describe_database_table
Mengambil struktur *schema* dari sebuah tabel spesifik.

- **Parameter:** `table_name` (String)
- **Output:** Informasi mengenai nama kolom, tipe data, dan atribut *nullable*.

## 3. read_hydroponic_table
Membaca deretan data terakhir (tanpa agregasi) dari tabel hidroponik dengan pembatasan (*LIMIT*).

- **Parameter:** `limit` (Int, Default: 5)
- **Output:** Kumpulan rekaman sensor dalam format JSON dengan Timestamp berbasis UUIDv7.

## 4. get_latest_sensor_data
Mendapatkan 1 *record* baris terakhir dari sensor, cocok untuk pengambilan kondisi *real-time* sistem tanpa menguras token yang besar.

## 5. get_sensor_data_summary (Analytics & Charting)
Alat analitik utama yang menggunakan fungsi TimescaleDB `time_bucket`. Tool ini mengelompokkan data dalam keranjang waktu tertentu dan memberikan rata-rata (AVG) tiap sensor. Sangat ideal untuk dimasukkan ke *prompt* saat LLM harus mendeskripsikan tren dalam grafik/chart.

- **Parameter:**
  - `num_buckets` (Int, Default: 7) - Berapa banyak kelompok yang ingin ditarik.
  - `bucket_width` (String, Default: "1 day") - Ukuran waktu tiap kelompok (contoh: "1 hour", "2 days").
- **Output:** Rata-rata *moisture*, suhu, *flowrate*, ph, dan tds per *bucket*.
