"""W-017 tests: st.components.v1.html → st.html migration shim."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_helper_imports_cleanly():
    """The helper module must import without side effects."""
    from dpsim.visualization.components import _html_helper
    assert callable(_html_helper.render_inline_html)


def test_all_migrated_components_import_cleanly():
    """Every component that used components.v1.html must still import."""
    # Side-effect-free import test — Streamlit is present in the venv.
    from dpsim.visualization.components import (  # noqa: F401
        column_xsec,
        impeller_xsec,
        impeller_xsec_v2,
        impeller_xsec_v2_2,
        impeller_xsec_v3,
    )


def test_default_path_uses_st_html(monkeypatch):
    """Without the env-var override, the helper should call st.html."""
    monkeypatch.delenv("DPSIM_USE_LEGACY_HTML", raising=False)
    from dpsim.visualization.components import _html_helper

    fake_st = MagicMock()
    fake_st.html = MagicMock()
    with patch.object(_html_helper, "st", fake_st):
        _html_helper.render_inline_html("<p>hi</p>", height_px=200)

    assert fake_st.html.called
    args, kwargs = fake_st.html.call_args
    body = args[0]
    assert "<p>hi</p>" in body
    assert "min-height:200px" in body
    assert kwargs.get("unsafe_allow_javascript") is True


def test_legacy_override_routes_to_components_v1(monkeypatch):
    """DPSIM_USE_LEGACY_HTML=1 must route through st.components.v1.html."""
    monkeypatch.setenv("DPSIM_USE_LEGACY_HTML", "1")
    from dpsim.visualization.components import _html_helper

    with patch("streamlit.components.v1.html") as fake_legacy:
        _html_helper.render_inline_html("<p>x</p>", height_px=100, scrolling=True)

    assert fake_legacy.called
    args, kwargs = fake_legacy.call_args
    assert args[0] == "<p>x</p>"
    assert kwargs.get("height") == 100
    assert kwargs.get("scrolling") is True


def test_scrolling_flag_applied_to_div(monkeypatch):
    monkeypatch.delenv("DPSIM_USE_LEGACY_HTML", raising=False)
    from dpsim.visualization.components import _html_helper

    fake_st = MagicMock()
    fake_st.html = MagicMock()
    with patch.object(_html_helper, "st", fake_st):
        _html_helper.render_inline_html("<x/>", height_px=50, scrolling=True)
        body = fake_st.html.call_args[0][0]
        assert "overflow:auto" in body

    fake_st.html.reset_mock()
    with patch.object(_html_helper, "st", fake_st):
        _html_helper.render_inline_html("<x/>", height_px=50, scrolling=False)
        body = fake_st.html.call_args[0][0]
        assert "overflow:hidden" in body


def test_fallback_when_st_html_missing(monkeypatch):
    """If st.html is not available (older Streamlit), fall back to legacy API."""
    monkeypatch.delenv("DPSIM_USE_LEGACY_HTML", raising=False)
    from dpsim.visualization.components import _html_helper

    fake_st_no_html = MagicMock(spec=[])  # spec=[] gives an object with NO attrs
    with patch.object(_html_helper, "st", fake_st_no_html):
        with patch("streamlit.components.v1.html") as fake_legacy:
            _html_helper.render_inline_html("<x/>", height_px=42)

    assert fake_legacy.called
    assert fake_legacy.call_args.kwargs.get("height") == 42


# ─── Full-document detection (post-2026-05-04 UI regression fix) ────────────


class TestFullDocumentDetection:
    """Full HTML documents must route to the iframe path even when st.html
    is available — DOMPurify can't compose them into the host page."""

    def test_doctype_html_routes_to_iframe(self, monkeypatch):
        monkeypatch.delenv("DPSIM_USE_LEGACY_HTML", raising=False)
        from dpsim.visualization.components import _html_helper

        fake_st = MagicMock()
        fake_st.html = MagicMock()
        with patch.object(_html_helper, "st", fake_st):
            with patch("streamlit.components.v1.html") as fake_legacy:
                _html_helper.render_inline_html(
                    "<!doctype html><html><body><svg/></body></html>",
                    height_px=380,
                )

        # Routed to iframe; st.html must NOT have been called.
        assert fake_legacy.called
        assert not fake_st.html.called

    def test_html_tag_routes_to_iframe(self, monkeypatch):
        """A document starting with <html> (no doctype) also routes to iframe."""
        monkeypatch.delenv("DPSIM_USE_LEGACY_HTML", raising=False)
        from dpsim.visualization.components import _html_helper

        fake_st = MagicMock()
        fake_st.html = MagicMock()
        with patch.object(_html_helper, "st", fake_st):
            with patch("streamlit.components.v1.html") as fake_legacy:
                _html_helper.render_inline_html(
                    "<html><body>x</body></html>", height_px=200,
                )
        assert fake_legacy.called
        assert not fake_st.html.called

    def test_doctype_case_insensitive(self, monkeypatch):
        monkeypatch.delenv("DPSIM_USE_LEGACY_HTML", raising=False)
        from dpsim.visualization.components import _html_helper

        for doctype in ("<!DOCTYPE html>", "<!Doctype HTML>", "<!doctype Html>"):
            fake_st = MagicMock()
            fake_st.html = MagicMock()
            with patch.object(_html_helper, "st", fake_st):
                with patch("streamlit.components.v1.html") as fake_legacy:
                    _html_helper.render_inline_html(
                        f"{doctype}<html><body>x</body></html>", height_px=100,
                    )
            assert fake_legacy.called, f"doctype {doctype!r} not detected"
            assert not fake_st.html.called

    def test_leading_whitespace_tolerated(self, monkeypatch):
        """Leading newlines/spaces don't disable doctype detection."""
        monkeypatch.delenv("DPSIM_USE_LEGACY_HTML", raising=False)
        from dpsim.visualization.components import _html_helper

        fake_st = MagicMock()
        fake_st.html = MagicMock()
        with patch.object(_html_helper, "st", fake_st):
            with patch("streamlit.components.v1.html") as fake_legacy:
                _html_helper.render_inline_html(
                    "\n\n  <!doctype html><html><body/></html>", height_px=100,
                )
        assert fake_legacy.called
        assert not fake_st.html.called

    def test_html_fragment_still_uses_st_html(self, monkeypatch):
        """A bare fragment (no doctype, no <html>) keeps using st.html."""
        monkeypatch.delenv("DPSIM_USE_LEGACY_HTML", raising=False)
        from dpsim.visualization.components import _html_helper

        fake_st = MagicMock()
        fake_st.html = MagicMock()
        with patch.object(_html_helper, "st", fake_st):
            with patch("streamlit.components.v1.html") as fake_legacy:
                _html_helper.render_inline_html(
                    "<div><svg><circle r='10'/></svg></div>", height_px=100,
                )
        assert fake_st.html.called
        assert not fake_legacy.called

    def test_real_asset_routes_to_iframe(self, monkeypatch):
        """The 5 production cross-section assets are full HTML documents
        and MUST route to the iframe path. Sample one to verify.
        """
        monkeypatch.delenv("DPSIM_USE_LEGACY_HTML", raising=False)
        from pathlib import Path

        from dpsim.visualization.components import _html_helper

        repo_root = Path(__file__).resolve().parents[2]
        asset = repo_root / "src" / "dpsim" / "visualization" / "components" \
            / "assets" / "impeller_xsec_v2_2.html"
        body = asset.read_text(encoding="utf-8")

        fake_st = MagicMock()
        fake_st.html = MagicMock()
        with patch.object(_html_helper, "st", fake_st):
            with patch("streamlit.components.v1.html") as fake_legacy:
                _html_helper.render_inline_html(body, height_px=388)
        assert fake_legacy.called
        assert not fake_st.html.called
