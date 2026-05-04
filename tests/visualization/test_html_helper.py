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
