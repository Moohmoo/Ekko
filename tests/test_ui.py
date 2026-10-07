import pytest
from agent.schemas import (
    AgentResponse,
    DoneEvent,
    ThoughtEvent,
    ToolCallEvent,
    ToolResultEvent,
)
from ui.console import (
    AgentUI,
    console,
    format_markdown_output,
    print_banner,
    prompt_user_input,
    render_thought_line,
)
from ui.presenter import ConsolePresenter, JsonPresenter



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


@pytest.mark.asyncio
async def test_console_presenter_render_stream() -> None:
    """Vérifie la consommation d'un flux d'événements par ConsolePresenter."""
    async def sample_stream():
        yield ThoughtEvent(thought="Réflexion test", elapsed=0.5)
        yield ToolCallEvent(tool_name="test_tool", arguments={"k": "v"})
        yield ToolResultEvent(tool_name="test_tool", result="succès")
        yield DoneEvent(response=AgentResponse(content="Réponse finale"))

    presenter = ConsolePresenter(debug=False)
    resp = await presenter.render_stream(sample_stream())
    assert resp is not None
    assert resp.content == "Réponse finale"


@pytest.mark.asyncio
async def test_json_presenter_render_stream(capsys) -> None:
    """Vérifie la sérialisation JSON stricte sur stdout par JsonPresenter."""
    async def sample_stream():
        yield DoneEvent(response=AgentResponse(content="JSON final"))

    presenter = JsonPresenter()
    resp = await presenter.render_stream(sample_stream())
    assert resp is not None
    assert resp.content == "JSON final"
    captured = capsys.readouterr()
    assert '"content": "JSON final"' in captured.out


def test_format_markdown_output_decompression() -> None:
    """Vérifie la décompression des titres et puces collés sur une seule ligne."""
    collapsed = "Titre - C'est quoi : X - Pourquoi : Y ### Titre B - Detail : Z"
    result = format_markdown_output(collapsed)
    assert "\n\n### Titre B" in result
    assert "\n- C'est quoi : X" in result
    assert "\n- Pourquoi : Y" in result
    assert "\n- Detail : Z" in result
