"""Unit tests for daemon hardware confinement and VRAM unloading management."""

from unittest.mock import patch

from ekko.daemon.resources import ResourceManager


def test_apply_process_niceness() -> None:
    """Ensure process priority is lowered using os.nice safely."""
    mgr = ResourceManager()
    with patch("os.nice", return_value=10) as mock_nice:
        val = mgr.apply_process_niceness(increment=10)
        assert val == 10
        mock_nice.assert_called_once_with(10)


def test_apply_process_niceness_handles_permission_error() -> None:
    """Ensure permission errors during nice increment are captured gracefully."""
    mgr = ResourceManager()
    with patch("os.nice", side_effect=PermissionError("Not permitted")):
        val = mgr.apply_process_niceness(increment=10)
        # Should return fallback without raising
        assert val >= 0


def test_inject_unload_vram_parameters() -> None:
    """Ensure keep_alive: '5m' is injected into LLM extra parameters to manage GPU VRAM TTL."""
    mgr = ResourceManager()

    # Empty kwargs
    params = mgr.inject_unload_vram({})
    assert params["extra_body"]["keep_alive"] == "5m"

    # Pre-existing extra_body
    existing = {"extra_body": {"custom_param": "foo"}}
    updated = mgr.inject_unload_vram(existing)
    assert updated["extra_body"]["keep_alive"] == "5m"
    assert updated["extra_body"]["custom_param"] == "foo"
