# Arsitektur & Alur Interaksi

Smart Hydroponic MCP Server berfungsi sebagai lapisan jembatan cerdas (*intelligent semantic bridge*) antara database time-series **TimescaleDB** dan **Large Language Models (LLM)**. Server ini menyediakan context feed, resource telemetri, dan tools analitik terparameterisasi tanpa mengizinkan LLM membuat kueri SQL sembarangan.

---

## 🏗️ Diagram Arsitektur Sistem

```mermaid
graph TB
    subgraph IoT_Hardware ["Perangkat Keras IoT (Terpisah)"]
        ESP32["ESP32 / Sensor Node"]
        PUMP["Water Pump & Relays"]
        LIGHT["Grow Light"]
    end

    subgraph Data_Layer ["Data & Storage Layer"]
        TSDB[("TimescaleDB (PostgreSQL)<br>Hypertable: hydroponic_data<br>Partition Key: UUIDv7 dataid")]
    end

    subgraph MCP_Server ["Smart Hydroponic MCP Server"]
        SQLA["SQLAlchemy 2.0 Async Engine<br>(Connection Pooling)"]
        FAST_MCP["FastMCP Server Core"]
        RES["MCP Resource: hydroponic://state/latest"]
        TOOLS["MCP Tools:<br>1. get_historical_trend<br>2. get_actuator_summary<br>3. get_sensor_data_summary"]
        PROMPT["MCP Prompt:<br>diagnose_environment"]
    end

    subgraph AI_Clients ["Ekosistem AI / LLM Agents"]
        CLAUDE["Claude Desktop / Cursor"]
        BACKEND_AI["Backend AI Service / LangChain"]
    end

    ESP32 -. Telemetry Ingestion .-> TSDB
    TSDB <==> SQLA
    SQLA <==> FAST_MCP
    FAST_MCP --- RES
    FAST_MCP --- TOOLS
    FAST_MCP --- PROMPT
    RES ==> CLAUDE
    TOOLS <==> CLAUDE
    PROMPT ==> CLAUDE
    RES ==> BACKEND_AI
    TOOLS <==> BACKEND_AI
```

---

## 🔒 Pemisahan Peran & Batasan Keamanan (Boundary Separation)

1. **MCP Server Sole Responsibility:**
   - Menyediakan data terkini (*real-time snapshot*) melalui resource `hydroponic://state/latest`.
   - Menjalankan agregasi downsampling melalui `time_bucket` per jam untuk metrik historis.
   - Menghitung keandalan sistem (uptime aktuator) secara presisi.
   - Mencegah *SQL Injection* dan *Context Window Overflow* dengan strictly typed tools dan parameterized raw SQL.
2. **Hardware Actuation:**
   - Perangkat keras dan aktuasi relay (pompa, lampu grow light) dikendalikan melalui service terpisah via protokol MQTT/CoAP. MCP Server tidak melakukan manipulasi status fisik secara langsung demi keamanan dan integritas kebun.

---

## 🔄 Alur Kerja Diagnosis Lingkungan (Agentic Sequence)

Alur berikut menggambarkan bagaimana Agen AI menggunakan Resource, Prompt, dan Tools MCP untuk mendiagnosis kondisi kebun secara mandiri:

```mermaid
sequenceDiagram
    autonumber
    actor User as Pengguna / Operator
    participant LLM as AI Agent (LLM)
    participant MCP as Smart Hydroponic MCP Server
    participant DB as TimescaleDB

    User->>LLM: "Bagaimana kondisi kebun hidroponik saya hari ini?"
    LLM->>MCP: Request Prompt: diagnose_environment
    MCP-->>LLM: Return instruksi & ambang batas agronomi (pH, TDS, Suhu, Kelembapan)

    LLM->>MCP: Read Resource: hydroponic://state/latest
    MCP->>DB: SELECT * FROM hydroponic_data ORDER BY dataid DESC LIMIT 1
    DB-->>MCP: Raw Latest Record
    MCP-->>LLM: Formatted Clean Telemetry State (pH, TDS, Temp, Humidity, Pump)

    Note over LLM: LLM mendeteksi suhu agak tinggi (29.5°C) dan ingin melihat tren 24 jam terakhir

    LLM->>MCP: Call Tool: get_historical_trend(metric='temperature_avg', hours=24)
    MCP->>DB: SELECT time_bucket('1 hour', dataid), AVG(...), MIN(...), MAX(...) WHERE dataid >= :min_uuid
    DB-->>MCP: Aggregated Hourly Buckets
    MCP-->>LLM: Downsampled Trend Data (24 baris teragregasi)

    LLM->>LLM: Reasoning & Analisis Agronomi
    LLM-->>User: Laporan Diagnosis Lengkap, Status Sistem (WARNING), & Rekomendasi Penyesuaian
```

---

## ⚡ Keunggulan Kombinasi SQLAlchemy 2.0 Core + Parameterized Raw SQL

1. **Koneksi Stabil & Efisien:** Menggunakan `create_async_engine` dan `async_sessionmaker` untuk manajemen pooling koneksi database asyncpg yang terlindungi dengan mekanisme *pre-ping* dan *graceful shutdown*.
2. **Performa Maksimal:** Mengabaikan overhead hidrasi objek ORM Python. Hasil query langsung dialirkan sebagai dictionary (`result.mappings()`).
3. **Pemanfaatan Penuh Fitur TimescaleDB:** Memungkinkan penggunaan langsung fungsi `time_bucket()`, operator interval PostgreSQL, dan perbandingan bit 48-bit UUIDv7 secara native.
