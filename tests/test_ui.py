from ui.console import (
    AgentUI,
    console,
    print_banner,
    prompt_user_input,
    render_thought_line,
)


def test_agent_ui_callbacks_dict() -> None:
    """Vérifie la présence des 4 callbacks requis dans le dictionnaire."""
    ui = AgentUI(debug=False)
    callbacks = ui.get_callbacks()
    assert "on_thinking_start" in callbacks
    assert "on_thought" in callbacks
    assert "on_tool_call" in callbacks
    assert "on_tool_result" in callbacks


def test_agent_ui_normal_lifecycle() -> None:
    """Vérifie le cycle d'affichage sans lever d'exception en mode normal."""
    ui = AgentUI(debug=False)
    ui.on_thinking_start()
    assert ui._status is not None

    ui.on_thought("Je prépare l'action")
    assert ui._status is None

    ui.on_tool_call("test_tool", {"param": 1})
    assert ui._status is not None

    ui.on_tool_result("test_tool", "succès")
    assert ui._status is None


def test_agent_ui_debug_lifecycle() -> None:
    """Vérifie le cycle d'affichage en mode debug verbeux."""
    ui = AgentUI(debug=True)
    ui.on_thinking_start()
    ui.on_thought("Pensée complète de debug")
    ui.on_tool_call("test_tool", {"arg": "val"})
    ui.on_tool_result("test_tool", "données brutes d'observation")
    assert ui._status is None


def test_agent_ui_stop_spinner_idempotent() -> None:
    """Vérifie que l'arrêt répété du spinner ne provoque pas d'erreur."""
    ui = AgentUI(debug=False)
    ui.stop_spinner()
    ui.stop_spinner()
    assert ui._status is None


def test_render_thought_line_truncation(capsys) -> None:
    """Vérifie le formatage et le tronquage d'une pensée longue."""
    long_thought = "A" * 120
    render_thought_line(long_thought, 1.5)
    # Ne lève pas d'exception


def test_print_banner_renders() -> None:
    """Vérifie que la bannière s'affiche sans erreur en mode normal et debug."""
    print_banner("qwen2.5:7b", "local", debug=False)
    print_banner("gemini-2.5-flash", "google", debug=True)


def test_prompt_user_input_success(monkeypatch) -> None:
    """Vérifie la capture d'une saisie utilisateur normale."""
    monkeypatch.setattr(console, "input", lambda _: "Bonjour Ekko")
    assert prompt_user_input() == "Bonjour Ekko"


def test_prompt_user_input_interrupt(monkeypatch) -> None:
    """Vérifie le retour 'exit' en cas d'interruption clavier."""
    def raise_interrupt(_):
        raise KeyboardInterrupt()

    monkeypatch.setattr(console, "input", raise_interrupt)
    assert prompt_user_input() == "exit"


def test_prompt_user_input_eof(monkeypatch) -> None:
    """Vérifie le retour 'exit' en cas de fermeture de flux EOF."""
    def raise_eof(_):
        raise EOFError()

    monkeypatch.setattr(console, "input", raise_eof)
    assert prompt_user_input() == "exit"
