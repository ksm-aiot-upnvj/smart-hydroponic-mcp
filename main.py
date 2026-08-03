from __future__ import annotations

import datetime
import os
import tomllib
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import UUID

import asyncpg
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP
from starlette.routing import Route

load_dotenv()

DEFAULT_DB_HOST = os.getenv("HYDROPONIC_DB_HOST", "127.0.0.1")
DEFAULT_DB_PORT = int(os.getenv("HYDROPONIC_DB_PORT", "5432"))
DEFAULT_DB_USER = os.getenv("HYDROPONIC_DB_USER")
DEFAULT_DB_NAME = os.getenv("HYDROPONIC_DB_NAME")
DEFAULT_DB_SCHEMA = os.getenv("HYDROPONIC_DB_SCHEMA", "public")
DB_PASSWORD = os.getenv("HYDROPONIC_DB_PASSWORD")
DEFAULT_TABLE_NAME = os.getenv("HYDROPONIC_TABLE_NAME", "hydroponic_data")

# ============ INISIALISASI MCP ============
mcp = FastMCP(
    name="Hydroponic MCP",
    stateless_http=True,
    json_response=True,
)

app = mcp.streamable_http_app()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Wildcard
    allow_credentials=False,  # FIXED: Cannot be true if wildcard is used
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
            "description": "MCP server for hydroponic database management",
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


# ============ CONNECTION POOLING ============
db_pool: asyncpg.Pool | None = None

original_lifespan = app.router.lifespan_context


@asynccontextmanager
async def app_lifespan(app):
    global db_pool
    if not all([DEFAULT_DB_USER, DEFAULT_DB_NAME, DB_PASSWORD]):
        raise RuntimeError("Database credentials tidak lengkap. Periksa file .env.")
    try:
        db_pool = await asyncpg.create_pool(
            host=DEFAULT_DB_HOST,
            port=DEFAULT_DB_PORT,
            database=DEFAULT_DB_NAME,
            user=DEFAULT_DB_USER,
            password=DB_PASSWORD,
            min_size=1,
            max_size=10,
            server_settings={
                "default_transaction_read_only": "on",
            },
        )
        print("✅ Database connection pool berhasil dibuat saat startup.")
    except Exception as e:
        raise RuntimeError(f"Gagal membuat database pool: {e}") from e

    async with original_lifespan(app) as state:
        yield state

    if db_pool:
        await db_pool.close()
        print(" Database connection pool ditutup.")


app.router.lifespan_context = app_lifespan


@asynccontextmanager
async def get_db_connection():
    """Context manager untuk mendapatkan koneksi secara efisien dari pool."""
    if not db_pool:
        raise RuntimeError(
            "Database pool belum diinisialisasi. Pastikan server dijalankan dengan benar."
        )

    async with db_pool.acquire() as conn:
        yield conn


# ============ UTILITY ============
async def _get_valid_columns(
    conn: asyncpg.Connection, table_name: str, target_columns: list[str]
) -> tuple[list[str], list[str]]:
    """Helper untuk memfilter kolom yang tersedia di tabel database."""
    col_query = "SELECT column_name FROM information_schema.columns WHERE table_schema = $1 AND table_name = $2"
    existing_cols = [
        r["column_name"]
        for r in await conn.fetch(col_query, DEFAULT_DB_SCHEMA, table_name)
    ]

    if not existing_cols:
        raise ValueError(f"Table tidak ditemukan: {DEFAULT_DB_SCHEMA}.{table_name}")

    valid_columns = [c for c in target_columns if c in existing_cols]
    if not valid_columns:
        valid_columns = ["*"]

    return valid_columns, existing_cols


def extract_timestamp_from_uuid(dataid: str) -> str:
    """Mengekstrak timestamp (waktu lokal/utc) dari UUIDv7."""
    try:
        timestamp_int = UUID(str(dataid)).time
        date = datetime.datetime.fromtimestamp(
            timestamp_int / 1_000,
            tz=datetime.datetime.now(datetime.UTC).tzinfo,
        )
        # Hapus milidetik agar lebih bersih untuk LLM
        return date.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:  # noqa: BLE001
        return ""


def _quote_ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _qualified_name(schema: str, table: str) -> str:
    return f"{_quote_ident(schema)}.{_quote_ident(table)}"


# ============ MCP TOOLS ============
@mcp.tool()
async def list_database_tables() -> list[str]:
    """List nama table dalam database hidroponik."""
    async with get_db_connection() as conn:
        query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = $1
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        rows = await conn.fetch(query, DEFAULT_DB_SCHEMA)
        return [row["table_name"] for row in rows]


@mcp.tool()
async def describe_database_table(table_name: str) -> list[dict[str, Any]]:
    """Lihat struktur kolom table database hidroponik."""
    async with get_db_connection() as conn:
        query = """
            SELECT
                column_name,
                data_type,
                is_nullable
            FROM information_schema.columns
            WHERE table_schema = $1
              AND table_name = $2
            ORDER BY ordinal_position
        """
        rows = await conn.fetch(query, DEFAULT_DB_SCHEMA, table_name)
        if not rows:
            raise ValueError(f"Table tidak ditemukan: {DEFAULT_DB_SCHEMA}.{table_name}")
        return [dict(row) for row in rows]


@mcp.tool()
async def read_hydroponic_table(limit: int = 5) -> list[dict[str, Any]]:
    """
    Baca data terakhir dari table hidroponik.
    Kolom otomatis difilter untuk menghemat token LLM.
    """
    async with get_db_connection() as conn:
        target_columns = [
            "dataid",
            "moisture_avg",
            "flowrate",
            "total_litres",
            "distance_cm",
            "ph",
            "tds",
            "temperature_avg",
            "humidity_avg",
            "pump_status",
            "light_status",
            "automation_status",
        ]
        valid_columns, existing_cols = await _get_valid_columns(
            conn, DEFAULT_TABLE_NAME, target_columns
        )

        select_clause = ", ".join([_quote_ident(c) for c in valid_columns])
        order_col = "dataid" if "dataid" in existing_cols else valid_columns[0]

        # Menggunakan parameter binding untuk LIMIT ($1)
        query = f"SELECT {select_clause} FROM {_qualified_name(DEFAULT_DB_SCHEMA, DEFAULT_TABLE_NAME)} ORDER BY {_quote_ident(order_col)} DESC LIMIT $1"
        rows = await conn.fetch(query, limit)

        result = []
        for row in rows:
            row_dict = dict(row)
            if row_dict.get("dataid"):
                row_dict["timestamp"] = extract_timestamp_from_uuid(row_dict["dataid"])
                row_dict["dataid"] = str(row_dict["dataid"])
            result.append(row_dict)

        return result


@mcp.tool()
async def get_latest_sensor_data() -> dict[str, Any]:
    """Ambil 1 data sensor paling terbaru (JSON Object)."""
    async with get_db_connection() as conn:
        target_columns = [
            "dataid",
            "moisture_avg",
            "flowrate",
            "total_litres",
            "distance_cm",
            "ph",
            "tds",
            "temperature_avg",
            "humidity_avg",
            "pump_status",
            "light_status",
            "automation_status",
        ]
        valid_columns, existing_cols = await _get_valid_columns(
            conn, DEFAULT_TABLE_NAME, target_columns
        )

        select_clause = ", ".join([_quote_ident(c) for c in valid_columns])
        order_col = "dataid" if "dataid" in existing_cols else valid_columns[0]

        query = f"SELECT {select_clause} FROM {_qualified_name(DEFAULT_DB_SCHEMA, DEFAULT_TABLE_NAME)} ORDER BY {_quote_ident(order_col)} DESC LIMIT 1"
        row = await conn.fetchrow(query)

        if not row:
            return {"message": "Data kosong"}

        row_dict = dict(row)
        if row_dict.get("dataid"):
            row_dict["timestamp"] = extract_timestamp_from_uuid(row_dict["dataid"])
            row_dict["dataid"] = str(row_dict["dataid"])

        return row_dict


@mcp.tool()
async def get_sensor_data_summary(
    num_buckets: int = 7, bucket_width: str = "1 day"
) -> list[dict[str, Any]]:
    """
    Ambil ringkasan agregasi data sensor (rata-rata) menggunakan TimescaleDB time_bucket UUIDv7.

    Args:
        num_buckets: Jumlah baris agregasi (misal 7 untuk 7 hari / 7 jam tergantung bucket_width)
        bucket_width: Lebar interval (misal '1 day', '2 days', '12 hours', '1 hour', '30 minutes', '1 week', '1 month')
    """
    if num_buckets <= 0 or num_buckets > 14:
        raise ValueError("num_buckets harus antara 1 sampai 14 untuk menghemat token.")

    async with get_db_connection() as conn:
        # Menggunakan time_bucket dari TimescaleDB 2.24+ yang mendukung UUIDv7 natively
        # ORDER BY bucket DESC + LIMIT akan mengambil <num_buckets> rentang waktu terakhir
        query = f"""
            SELECT 
                time_bucket($1::text::interval, dataid) AS bucket_time,
                ROUND(AVG(temperature_avg)::numeric, 2) AS temp_avg,
                ROUND(AVG(humidity_avg)::numeric, 2) AS hum_avg,
                ROUND(AVG(moisture_avg)::numeric, 2) AS moist_avg,
                ROUND(AVG(ph)::numeric, 2) AS ph_avg,
                ROUND(AVG(tds)::numeric, 2) AS tds_avg,
                ROUND(AVG(flowrate)::numeric, 2) AS flow_avg
            FROM {_qualified_name(DEFAULT_DB_SCHEMA, DEFAULT_TABLE_NAME)}
            GROUP BY bucket_time
            ORDER BY bucket_time DESC
            LIMIT $2
        """

        rows = await conn.fetch(query, bucket_width, num_buckets)

        result = []
        for row in rows:
            row_dict = dict(row)
            # Konversi kolom timestamp TimescaleDB menjadi string
            if row_dict.get("bucket_time"):
                row_dict["timestamp"] = row_dict["bucket_time"].strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                del row_dict["bucket_time"]
            result.append(row_dict)

        return result


# ============ RUN SERVER ============
if __name__ == "__main__":
    if not all([DEFAULT_DB_USER, DEFAULT_DB_NAME, DB_PASSWORD]):
        print("  PERINGATAN: Environment variables database belum lengkap!")
        print(
            "   Pastikan HYDROPONIC_DB_USER, HYDROPONIC_DB_NAME, dan HYDROPONIC_DB_PASSWORD di-set di file .env\n"
        )

    print(" Menjalankan Hydroponic MCP Server...")
    print(f" Database: {DEFAULT_DB_NAME} (user: {DEFAULT_DB_USER})")

    import uvicorn

    uvicorn.run(
        app,
        log_level="info",
    )
