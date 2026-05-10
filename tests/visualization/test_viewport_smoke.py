"""Optional browser-level viewport smoke tests for the Streamlit shell.

These tests are gated by DPSIM_RUN_BROWSER_TESTS=1 because CI and local
dev environments do not always have Playwright browsers installed. When
enabled, they exercise the layout contract created by the UI optimization
plan: app shell loads, the run rail exists, and constrained viewports do
not produce a blank page.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from urllib.request import urlopen

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("DPSIM_RUN_BROWSER_TESTS") != "1",
    reason="Set DPSIM_RUN_BROWSER_TESTS=1 to run optional browser viewport smoke tests.",
)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(port: int, timeout_s: float = 30.0) -> None:
    deadline = time.time() + timeout_s
    url = f"http://127.0.0.1:{port}/_stcore/health"
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except Exception as exc:  # noqa: BLE001 - readiness polling
            last_error = exc
        time.sleep(0.5)
    raise AssertionError(f"Streamlit did not become healthy: {last_error}")


@contextmanager
def _streamlit_server() -> Iterator[int]:
    repo = Path(__file__).resolve().parents[2]
    port = _free_port()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(repo / "src" / "dpsim" / "visualization" / "app.py"),
            "--server.headless=true",
            f"--server.port={port}",
            "--browser.gatherUsageStats=false",
        ],
        cwd=repo,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_health(port)
        yield port
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.mark.parametrize("width,height", [(1440, 1000), (1280, 800), (1024, 768), (390, 844)])
def test_streamlit_shell_viewport_smoke(width: int, height: int):
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright

    with _streamlit_server() as port:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(f"http://127.0.0.1:{port}", wait_until="domcontentloaded")
            page.get_by_text("DPSim").first.wait_for(timeout=30_000)
            page.get_by_text("Last run").first.wait_for(timeout=30_000)
            body_text = page.locator("body").inner_text(timeout=10_000)
            assert body_text.strip()
            assert "Target profile" in body_text or width < 500
            assert "Evidence roll-up" in body_text or "EVIDENCE ROLL-UP" in body_text
            assert "Traceback" not in body_text
            browser.close()


def test_streamlit_shell_representative_stage_routes():
    pytest.importorskip("playwright.sync_api")
    from playwright.sync_api import sync_playwright

    expected_stage_text = {
        "target": "Target Product Profile",
        "m3": "M3 Column Method Context",
        "run": "Run full lifecycle",
        "validation": "Validation & evidence",
        "calibrate": "Calibration store",
    }
    with _streamlit_server() as port:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            for stage, expected in expected_stage_text.items():
                page.goto(
                    f"http://127.0.0.1:{port}/?dpsim_stage={stage}",
                    wait_until="domcontentloaded",
                )
                page.get_by_text("DPSim").first.wait_for(timeout=30_000)
                page.get_by_text(expected).first.wait_for(timeout=30_000)
                body_text = page.locator("body").inner_text(timeout=10_000)
                assert expected in body_text
                assert "Traceback" not in body_text
            browser.close()
