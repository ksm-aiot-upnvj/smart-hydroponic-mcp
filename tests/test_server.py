from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from main import (
    ActuatorType,
    MetricType,
    _qualified_name,
    _quote_ident,
    app,
    diagnose_environment,
    extract_timestamp_from_uuid,
    get_actuator_summary,
    get_historical_trend,
    get_latest_sensor_data,
    get_latest_state,
    get_min_uuidv7_from_timestamp,
)


class MockMappingResult:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def all(self) -> list[dict]:
        return self._rows

    def first(self) -> dict | None:
        return self._rows[0] if self._rows else None


class MockExecuteResult:
    def __init__(self, rows: list[dict]):
        self._mapping = MockMappingResult(rows)

    def mappings(self) -> MockMappingResult:
        return self._mapping


# ============ UNIT TESTS: UTILITIES ============
def test_quote_ident():
    assert _quote_ident("table_name") == '"table_name"'
    assert _quote_ident('col"name') == '"col""name"'


def test_qualified_name():
    assert _qualified_name("public", "hydroponic_data") == '"public"."hydroponic_data"'


def test_uuidv7_timestamp_extraction():
    now = datetime.datetime(2026, 9, 5, 10, 30, 0, tzinfo=datetime.UTC)
    ms = int(now.timestamp() * 1000)
    test_uuid = UUID(int=(ms << 80))

    extracted_str = extract_timestamp_from_uuid(test_uuid)
    assert extracted_str == "2026-09-05 10:30:00"

    # Test invalid UUID fallback
    assert extract_timestamp_from_uuid("invalid-uuid") == ""


def test_get_min_uuidv7_from_timestamp():
    dt = datetime.datetime(2026, 9, 5, 12, 0, 0, tzinfo=datetime.UTC)
    expected_ms = int(dt.timestamp() * 1000)
    bound_uuid = get_min_uuidv7_from_timestamp(dt)

    assert (bound_uuid.int >> 80) == expected_ms


# ============ UNIT TESTS: MCP PROMPTS ============
def test_diagnose_environment_prompt():
    prompt_text = diagnose_environment()
    assert "hydroponic://state/latest" in prompt_text
    assert "pH: 5.5 - 6.5" in prompt_text
    assert "TDS: 800 - 1200 ppm" in prompt_text
    assert "STATUS SISTEM" in prompt_text
    assert "get_historical_trend" in prompt_text
    assert "get_actuator_summary" in prompt_text


# ============ UNIT TESTS: MCP RESOURCES ============
@pytest.mark.asyncio
async def test_resource_get_latest_state_empty():
    mock_session = AsyncMock()
    mock_session.execute.return_value = MockExecuteResult([])

    with patch("main.get_db_session") as mock_get_session:
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_session
        mock_ctx.__aexit__.return_value = None
        mock_get_session.return_value = mock_ctx

        result = await get_latest_state()
        assert "DATA KOSONG" in result


@pytest.mark.asyncio
async def test_resource_get_latest_state_populated():
    fake_row = {
        "dataid": "01920000-0000-7000-8000-000000000000",
        "ph": 6.25,
        "tds": 950.0,
        "flowrate": 1.5,
        "total_litres": 140.2,
        "distance_cm": 12.5,
        "temperature_avg": 24.6,
        "temperature_atas": 25.0,
        "temperature_bawah": 24.2,
        "humidity_avg": 65.4,
        "humidity_atas": 66.0,
        "humidity_bawah": 64.8,
        "moisture_avg": 72.0,
        "pump_status": True,
        "light_status": False,
        "automation_status": True,
    }

    mock_session = AsyncMock()
    mock_session.execute.return_value = MockExecuteResult([fake_row])

    with patch("main.get_db_session") as mock_get_session:
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_session
        mock_ctx.__aexit__.return_value = None
        mock_get_session.return_value = mock_ctx

        result = await get_latest_state()
        assert "[TELEMETRI TERKINI]" in result
        assert "pH=6.25" in result
        assert "TDS=950.0ppm" in result
        assert "Pompa=ACTIVE (ON)" in result
        assert "GrowLight=INACTIVE (OFF)" in result
        assert "Otomasi=ACTIVE (AUTO)" in result


# ============ UNIT TESTS: MCP TOOLS ============
@pytest.mark.asyncio
async def test_tool_get_historical_trend():
    bucket_dt = datetime.datetime(2026, 9, 5, 8, 0, 0, tzinfo=datetime.UTC)
    fake_trend = [
        {
            "bucket_time": bucket_dt,
            "avg_val": 6.20,
            "min_val": 6.10,
            "max_val": 6.35,
            "sample_count": 60,
        }
    ]

    mock_session = AsyncMock()
    mock_session.execute.return_value = MockExecuteResult(fake_trend)

    with patch("main.get_db_session") as mock_get_session:
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_session
        mock_ctx.__aexit__.return_value = None
        mock_get_session.return_value = mock_ctx

        result = await get_historical_trend(metric=MetricType.ph, hours=12)
        assert len(result) == 1
        assert result[0]["metric"] == "ph"
        assert result[0]["average"] == 6.20
        assert result[0]["min"] == 6.10
        assert result[0]["max"] == 6.35
        assert result[0]["samples"] == 60


@pytest.mark.asyncio
async def test_tool_get_actuator_summary():
    fake_summary = {
        "total_samples": 120,
        "active_samples": 90,
        "uptime_percentage": 75.0,
    }

    mock_session = AsyncMock()
    mock_session.execute.return_value = MockExecuteResult([fake_summary])

    with patch("main.get_db_session") as mock_get_session:
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_session
        mock_ctx.__aexit__.return_value = None
        mock_get_session.return_value = mock_ctx

        res = await get_actuator_summary(actuator=ActuatorType.pump_status, hours=24)
        assert res["actuator"] == "pump_status"
        assert res["total_samples"] == 120
        assert res["active_samples"] == 90
        assert res["uptime_percentage"] == 75.0
        assert res["status"] == "NORMAL"


@pytest.mark.asyncio
async def test_tool_get_latest_sensor_data():
    fake_row = {
        "dataid": "01920000-0000-7000-8000-000000000000",
        "ph": 6.1,
        "tds": 900.0,
    }

    mock_session = AsyncMock()
    mock_session.execute.return_value = MockExecuteResult([fake_row])

    with patch("main.get_db_session") as mock_get_session:
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_session
        mock_ctx.__aexit__.return_value = None
        mock_get_session.return_value = mock_ctx

        data = await get_latest_sensor_data()
        assert data["ph"] == 6.1
        assert data["tds"] == 900.0
        assert "timestamp" in data


# ============ INTEGRATION TESTS: HTTP ENDPOINTS ============
@pytest.mark.asyncio
async def test_fastapi_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Test Root
        res_root = await ac.get("/")
        assert res_root.status_code == 200
        root_data = res_root.json()
        assert root_data["status"] == "running"
        assert "Hydroponic MCP" in root_data["name"]

        # Test Health
        res_health = await ac.get("/health")
        assert res_health.status_code == 200
        assert res_health.json()["status"] == "healthy"
