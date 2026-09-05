from __future__ import annotations

import datetime
import os
import tomllib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP
from pydantic import Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from starlette.routing import Route

load_dotenv()

DEFAULT_DB_HOST = os.getenv("HYDROPONIC_DB_HOST", "127.0.0.1")
DEFAULT_DB_PORT = int(os.getenv("HYDROPONIC_DB_PORT", "5432"))
DEFAULT_DB_USER = os.getenv("HYDROPONIC_DB_USER", "admin_iot_db")
DEFAULT_DB_NAME = os.getenv("HYDROPONIC_DB_NAME", "iot_hydroponik")
DEFAULT_DB_SCHEMA = os.getenv("HYDROPONIC_DB_SCHEMA", "public")
DB_PASSWORD = os.getenv("HYDROPONIC_DB_PASSWORD", "")
DEFAULT_TABLE_NAME = os.getenv("HYDROPONIC_TABLE_NAME", "hydroponic_data")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql+asyncpg://{DEFAULT_DB_USER}:{DB_PASSWORD}@{DEFAULT_DB_HOST}:{DEFAULT_DB_PORT}/{DEFAULT_DB_NAME}",
)

# ============ INISIALISASI MCP ============
mcp = FastMCP(
    name="Hydroponic MCP",
    stateless_http=True,
    json_response=True,
    transport_security={"allowed_hosts": ["*"]},
)

app = mcp.sse_app()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_version() -> str:
    try:
        pyproject_path = Path(__file__).parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            return tomllib.load(f)["project"]["version"]
    except Exception:  # noqa: BLE001
        return "unknown"


async def root_endpoint(request):
    """Root endpoint with server info."""
    return JSONResponse(
        {
            "name": "Hydroponic MCP Server",
            "version": get_version(),
            "status": "running",
            "description": "Semantic MCP server for smart hydroponic telemetry and analytics",
            "database_engine": "SQLAlchemy 2.0 (Async Core)",
        }
    )


async def health_endpoint(request):
    """Health check endpoint."""
    return JSONResponse({"status": "healthy", "service": "Hydroponic MCP"})


app.routes.extend(
    [
        Route("/", endpoint=root_endpoint),
        Route("/health", endpoint=health_endpoint),
    ]
)


# ============ SQLALCHEMY ENGINE & SESSION LIFECYCLE ============
engine: AsyncEngine | None = None
async_session_maker: async_sessionmaker[AsyncSession] | None = None

original_lifespan = app.router.lifespan_context


@asynccontextmanager
async def app_lifespan(app):
    global engine, async_session_maker
    if not DB_PASSWORD and "DATABASE_URL" not in os.environ:
        print("⚠️ PERINGATAN: Database credentials belum lengkap di .env.")

    try:
        engine = create_async_engine(
            DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
        async_session_maker = async_sessionmaker(
            engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )
        print("✅ SQLAlchemy Async Engine & Sessionmaker berhasil dibuat saat startup.")
    except Exception as e:  # noqa: BLE001
        print(f"⚠️ Gagal membuat SQLAlchemy async engine: {e}")

    async with original_lifespan(app) as state:
        yield state

    if engine:
        await engine.dispose()
        print("🔌 SQLAlchemy Async Engine connection pool ditutup.")


app.router.lifespan_context = app_lifespan


@asynccontextmanager
async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Context manager untuk mendapatkan AsyncSession dari SQLAlchemy session factory."""
    if not async_session_maker:
        raise RuntimeError(
            "Database session factory belum diinisialisasi. Pastikan konfigurasi database sudah benar."
        )

    async with async_session_maker() as session:
        yield session


# ============ UTILITY FUNCTIONS ============
def _quote_ident(value: str) -> str:
    """Escaping nama identifier kolom/tabel untuk mencegah SQL injection."""
    return '"' + value.replace('"', '""') + '"'


def _qualified_name(schema: str, table: str) -> str:
    """Menggabungkan schema dan tabel secara aman."""
    return f"{_quote_ident(schema)}.{_quote_ident(table)}"


def extract_timestamp_from_uuid(dataid: Any) -> str:
    """
    Mengekstrak timestamp (UTC) dari 48-bit pertama UUIDv7.
    """
    try:
        u = UUID(str(dataid))
        timestamp_ms = u.int >> 80
        date = datetime.datetime.fromtimestamp(
            timestamp_ms / 1000.0,
            tz=datetime.UTC,
        )
        return date.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:  # noqa: BLE001
        return ""


def get_min_uuidv7_from_timestamp(dt: datetime.datetime) -> UUID:
    """
    Menghasilkan boundary UUID minimum untuk rentang waktu tertentu
    berdasarkan struktur bit 48-bit timestamp UUIDv7.
    """
    timestamp_ms = int(dt.timestamp() * 1000)
    return UUID(int=(timestamp_ms << 80))


# ============ ENUMS & SCHEMAS ============
class MetricType(str, Enum):
    ph = "ph"
    tds = "tds"
    temperature_avg = "temperature_avg"
    humidity_avg = "humidity_avg"
    moisture_avg = "moisture_avg"
    flowrate = "flowrate"
    total_litres = "total_litres"
    distance_cm = "distance_cm"


class ActuatorType(str, Enum):
    pump_status = "pump_status"
    light_status = "light_status"
    automation_status = "automation_status"


# ============ MCP RESOURCES ============
@mcp.resource("hydroponic://state/latest")
async def get_latest_state() -> str:
    """Status telemetri terkini (kualitas air, iklim mikro, aktuator) dalam format teks terstruktur."""
    table_ref = _qualified_name(DEFAULT_DB_SCHEMA, DEFAULT_TABLE_NAME)
    query = text(f"SELECT * FROM {table_ref} ORDER BY dataid DESC LIMIT 1")

    async with get_db_session() as session:
        result = await session.execute(query)
        row = result.mappings().first()

    if not row:
        return "DATA KOSONG: Tabel sensor hidroponik belum memiliki rekaman data."

    timestamp_str = extract_timestamp_from_uuid(row.get("dataid", ""))

    def _fmt(val: Any, prec: int = 2) -> str:
        if val is None:
            return "N/A"
        try:
            return f"{float(val):.{prec}f}"
        except ValueError, TypeError:
            return str(val)

    pump_str = "ACTIVE (ON)" if row.get("pump_status") else "INACTIVE (OFF)"
    light_str = "ACTIVE (ON)" if row.get("light_status") else "INACTIVE (OFF)"
    auto_str = "ACTIVE (AUTO)" if row.get("automation_status") else "MANUAL"

    return f"""[TELEMETRI TERKINI] ID:{row.get("dataid")} | Waktu(UTC):{timestamp_str or "Unknown"}
Kualitas Air: pH={_fmt(row.get("ph"), 2)} (ideal 5.5-6.5) | TDS={_fmt(row.get("tds"), 1)}ppm (ideal 800-1200) | Aliran={_fmt(row.get("flowrate"), 2)}L/min | TotalAir={_fmt(row.get("total_litres"), 2)}L | JarakTandon={_fmt(row.get("distance_cm"), 1)}cm
Iklim Mikro: SuhuAvg={_fmt(row.get("temperature_avg"), 1)}°C (Atas:{_fmt(row.get("temperature_atas"), 1)}, Bawah:{_fmt(row.get("temperature_bawah"), 1)}) | HumAvg={_fmt(row.get("humidity_avg"), 1)}% (Atas:{_fmt(row.get("humidity_atas"), 1)}, Bawah:{_fmt(row.get("humidity_bawah"), 1)}) | LengasTanah={_fmt(row.get("moisture_avg"), 1)}%
Aktuator: Pompa={pump_str} | GrowLight={light_str} | Otomasi={auto_str}"""


# ============ MCP TOOLS ============
@mcp.tool()
async def get_historical_trend(
    metric: Annotated[
        MetricType,
        Field(description="Nama metrik telemetri yang dianalisis."),
    ],
    hours: Annotated[
        int,
        Field(
            default=24,
            description="Rentang waktu mundur dalam jam (1-168, default 24).",
            ge=1,
            le=168,
        ),
    ] = 24,
) -> list[dict[str, Any]]:
    """Ambil tren agregasi sensor per jam (avg, min, max, samples) untuk rentang waktu jam tertentu."""
    table_ref = _qualified_name(DEFAULT_DB_SCHEMA, DEFAULT_TABLE_NAME)
    metric_col = _quote_ident(metric.value)

    start_time = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=hours)
    min_uuid = get_min_uuidv7_from_timestamp(start_time)

    # Parameterized raw SQL dengan :min_uuid dan time_bucket TimescaleDB
    query = text(f"""
        SELECT 
            time_bucket('1 hour', dataid) AS bucket_time,
            ROUND(AVG({metric_col})::numeric, 2) AS avg_val,
            ROUND(MIN({metric_col})::numeric, 2) AS min_val,
            ROUND(MAX({metric_col})::numeric, 2) AS max_val,
            COUNT(*)::int AS sample_count
        FROM {table_ref}
        WHERE dataid >= :min_uuid
        GROUP BY bucket_time
        ORDER BY bucket_time DESC
    """)

    async with get_db_session() as session:
        result = await session.execute(query, {"min_uuid": min_uuid})
        rows = result.mappings().all()

    output = []
    for r in rows:
        bucket_time = r.get("bucket_time")
        ts_str = (
            bucket_time.strftime("%Y-%m-%d %H:%M:%S")
            if hasattr(bucket_time, "strftime")
            else str(bucket_time)
        )
        output.append(
            {
                "timestamp": ts_str,
                "metric": metric.value,
                "average": float(r["avg_val"])
                if r.get("avg_val") is not None
                else None,
                "min": float(r["min_val"]) if r.get("min_val") is not None else None,
                "max": float(r["max_val"]) if r.get("max_val") is not None else None,
                "samples": r.get("sample_count", 0),
            }
        )

    return output


@mcp.tool()
async def get_actuator_summary(
    actuator: Annotated[
        ActuatorType,
        Field(description="Nama aktuator yang dievaluasi."),
    ],
    hours: Annotated[
        int,
        Field(
            default=24,
            description="Rentang waktu mundur dalam jam (1-168, default 24).",
            ge=1,
            le=168,
        ),
    ] = 24,
) -> dict[str, Any]:
    """Hitung persentase uptime dan total sampel aktif aktuator dalam rentang jam tertentu."""
    table_ref = _qualified_name(DEFAULT_DB_SCHEMA, DEFAULT_TABLE_NAME)
    actuator_col = _quote_ident(actuator.value)

    start_time = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=hours)
    min_uuid = get_min_uuidv7_from_timestamp(start_time)

    query = text(f"""
        SELECT 
            COUNT(*)::int AS total_samples,
            COUNT(*) FILTER (WHERE {actuator_col} IS TRUE)::int AS active_samples,
            ROUND((COUNT(*) FILTER (WHERE {actuator_col} IS TRUE)::numeric / NULLIF(COUNT(*), 0) * 100.0), 2) AS uptime_percentage
        FROM {table_ref}
        WHERE dataid >= :min_uuid
    """)

    async with get_db_session() as session:
        result = await session.execute(query, {"min_uuid": min_uuid})
        row = result.mappings().first()

    total_samples = row["total_samples"] if row and row.get("total_samples") else 0
    active_samples = row["active_samples"] if row and row.get("active_samples") else 0
    uptime_pct = (
        float(row["uptime_percentage"])
        if row and row.get("uptime_percentage") is not None
        else 0.0
    )

    return {
        "actuator": actuator.value,
        "window_hours": hours,
        "since_utc": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_samples": total_samples,
        "active_samples": active_samples,
        "uptime_percentage": uptime_pct,
        "status": "NORMAL" if total_samples > 0 else "NO_DATA",
    }


@mcp.tool()
async def get_latest_sensor_data() -> dict[str, Any]:
    """Ambil 1 rekaman data sensor paling baru dalam format JSON dictionary."""
    table_ref = _qualified_name(DEFAULT_DB_SCHEMA, DEFAULT_TABLE_NAME)
    query = text(f"SELECT * FROM {table_ref} ORDER BY dataid DESC LIMIT 1")

    async with get_db_session() as session:
        result = await session.execute(query)
        row = result.mappings().first()

    if not row:
        return {"message": "Data kosong"}

    row_dict = dict(row)
    if row_dict.get("dataid"):
        row_dict["timestamp"] = extract_timestamp_from_uuid(row_dict["dataid"])
        row_dict["dataid"] = str(row_dict["dataid"])

    return row_dict


@mcp.tool()
async def get_sensor_data_summary(
    num_buckets: Annotated[
        int,
        Field(
            default=7,
            description="Jumlah interval waktu (1-14, default 7).",
            ge=1,
            le=14,
        ),
    ] = 7,
    bucket_width: Annotated[
        str,
        Field(
            default="1 day",
            description="Lebar interval TimescaleDB (misal: '1 hour', '12 hours', '1 day').",
        ),
    ] = "1 day",
) -> list[dict[str, Any]]:
    """Ambil ringkasan agregasi rata-rata multi-sensor berdasarkan interval waktu TimescaleDB."""
    if num_buckets <= 0 or num_buckets > 14:
        raise ValueError("num_buckets harus antara 1 sampai 14 untuk menghemat token.")

    table_ref = _qualified_name(DEFAULT_DB_SCHEMA, DEFAULT_TABLE_NAME)
    query = text(f"""
        SELECT 
            time_bucket(:bucket_width::interval, dataid) AS bucket_time,
            ROUND(AVG(temperature_avg)::numeric, 2) AS temp_avg,
            ROUND(AVG(humidity_avg)::numeric, 2) AS hum_avg,
            ROUND(AVG(moisture_avg)::numeric, 2) AS moist_avg,
            ROUND(AVG(ph)::numeric, 2) AS ph_avg,
            ROUND(AVG(tds)::numeric, 2) AS tds_avg,
            ROUND(AVG(flowrate)::numeric, 2) AS flow_avg
        FROM {table_ref}
        GROUP BY bucket_time
        ORDER BY bucket_time DESC
        LIMIT :num_buckets
    """)

    async with get_db_session() as session:
        result = await session.execute(
            query, {"bucket_width": bucket_width, "num_buckets": num_buckets}
        )
        rows = result.mappings().all()

    output = []
    for row in rows:
        row_dict = dict(row)
        if row_dict.get("bucket_time"):
            bt = row_dict["bucket_time"]
            row_dict["timestamp"] = (
                bt.strftime("%Y-%m-%d %H:%M:%S") if hasattr(bt, "strftime") else str(bt)
            )
            del row_dict["bucket_time"]
        output.append(row_dict)

    return output


@mcp.tool()
async def list_database_tables() -> list[str]:
    """Daftar nama tabel dalam database hidroponik."""
    query = text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = :schema
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    async with get_db_session() as session:
        result = await session.execute(query, {"schema": DEFAULT_DB_SCHEMA})
        return [row["table_name"] for row in result.mappings().all()]


@mcp.tool()
async def describe_database_table(
    table_name: Annotated[str, Field(description="Nama tabel yang diperiksa.")],
) -> list[dict[str, Any]]:
    """Daftar kolom, tipe data, dan status nullable dari tabel tertentu."""
    query = text("""
        SELECT
            column_name,
            data_type,
            is_nullable
        FROM information_schema.columns
        WHERE table_schema = :schema
          AND table_name = :table
        ORDER BY ordinal_position
    """)
    async with get_db_session() as session:
        result = await session.execute(
            query, {"schema": DEFAULT_DB_SCHEMA, "table": table_name}
        )
        rows = [dict(r) for r in result.mappings().all()]
        if not rows:
            raise ValueError(f"Table tidak ditemukan: {DEFAULT_DB_SCHEMA}.{table_name}")
        return rows


# ============ MCP PROMPTS ============
@mcp.prompt()
def diagnose_environment() -> str:
    """Prompt workflow terstandarisasi untuk diagnosis lingkungan hidroponik."""
    return """Peran: Pakar Agronomi & IoT Hidroponik Cerdas.
Tugas: Diagnosis kesehatan sistem hidroponik berdasarkan data telemetri.

Alur Kerja:
1. Baca resource `hydroponic://state/latest`.
2. Evaluasi metrik terhadap ambang batas acuan:
   - pH: 5.5 - 6.5 (Kritis: <5.0 merusak akar, >7.5 nutrient lockout).
   - TDS: 800 - 1200 ppm (Kritis: <600 ppm malnutrisi, >1400 ppm salt stress / daun terbakar).
   - Suhu: 20.0 - 28.0 °C (Kritis: >30.0 °C oksigen larutan turun drastis, risiko Pythium/busuk akar).
   - Kelembapan: 50 - 70 % (Kritis: >80% risiko jamur daun).
   - Aliran & Pompa: Jika Pompa=ACTIVE tapi Aliran=0 L/min -> indikasi pompa macet atau pipa bocor.
   - Tandon: Pastikan JarakTandon aman (tidak mendekati dasar/kering).
3. Jika butuh data tren, panggil `get_historical_trend(metric, hours)`.
4. Jika butuh riwayat keaktifan pompa, panggil `get_actuator_summary(actuator='pump_status', hours=24)`.
5. Format Laporan Singkat:
   - STATUS SISTEM: [HEALTHY / WARNING / CRITICAL]
   - EVALUASI PARAMETER: Nilai aktual vs batas ideal.
   - TEMUAN ANOMALI: Masalah/risiko yang terdeteksi.
   - REKOMENDASI TINDAKAN: Langkah perbaikan segera.
"""


# ============ RUN SERVER ============
if __name__ == "__main__":
    if not DB_PASSWORD and "DATABASE_URL" not in os.environ:
        print("⚠️  PERINGATAN: Environment variables database belum lengkap!")
        print(
            "   Pastikan HYDROPONIC_DB_USER, HYDROPONIC_DB_NAME, dan HYDROPONIC_DB_PASSWORD di-set di file .env\n"
        )

    print("🌱 Menjalankan Hydroponic MCP Server (SQLAlchemy Core + Raw SQL Engine)...")
    print(f"📊 Database: {DEFAULT_DB_NAME} (user: {DEFAULT_DB_USER})")

    import uvicorn

    uvicorn.run(
        app,
        log_level="info",
    )
