#!/usr/bin/env python3
"""Interactive test script for Mascot Emotions & Daemon Load Simulation.

Permits triggering real conditions to verify all 7 Mascot micro-emotions:
- welcome : First launch state (empty database, no signals, no notes)
- idle : Nominal resting state
- hover_drop : User drag-over dropzone
- ingesting : Active background distillation
- ready : Post-distillation success state
- alert : Critical blindspot signal pending
- error : File > 25MB rejection or daemon failure
"""

import json
from pathlib import Path
import socket
import sys
import tempfile
import time


SOCKET_PATH = "/tmp/ekko.sock"


def send_rpc(method: str, params: dict | None = None) -> dict:
    """Send JSON-RPC command to local Ekko daemon socket."""
    if not Path(SOCKET_PATH).exists():
        print(f"[Test:ERROR] Socket {SOCKET_PATH} introuvable. Le daemon est-il lancé ?")
        return {"error": "Socket not found"}

    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        client.connect(SOCKET_PATH)
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {},
        }
        client.sendall(json.dumps(payload).encode("utf-8") + b"\n")
        response_data = b""
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            response_data += chunk
            if b"\n" in chunk:
                break
        if response_data:
            return json.loads(response_data.decode("utf-8").strip())
        return {"error": "Empty response"}
    finally:
        client.close()


def test_error_payload() -> None:
    """Test 'error' emotion by sending a file exceeding 25MB threshold."""
    print("\n[1/3] Test de l'émotion 'error' (Rejet fichier > 25 Mo)...")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        # Create 26MB sparse file
        f.seek(26 * 1024 * 1024 - 1)
        f.write(b"\0")
        heavy_file_path = f.name

    try:
        print(f"-> Envoi d'un fichier lourd factice de 26 Mo ({heavy_file_path})...")
        res = send_rpc("ingest_file", {"file_path": heavy_file_path})
        print(f"<- Réponse daemon : {res}")
    finally:
        Path(heavy_file_path).unlink(missing_ok=True)


def test_ingesting_and_ready() -> None:
    """Test 'ingesting' and 'ready' emotions via small document drop."""
    print("\n[2/3] Test des émotions 'ingesting' et 'ready' (Ingestion document valide)...")
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
        f.write("# Test Note Ekko\n\nContenu synthétique pour validation du cycle d'émotions.")
        test_file = f.name

    try:
        print(f"-> Ingestion d'une note valide ({test_file})...")
        res = send_rpc("ingest_file", {"file_path": test_file})
        print(f"<- Réponse daemon : {res}")
    finally:
        Path(test_file).unlink(missing_ok=True)


def test_alert_signal() -> None:
    """Display pending signals that trigger 'alert' emotion."""
    print("\n[3/3] Test de l'émotion 'alert' (Vérification signaux non lus)...")
    res = send_rpc("get_pending_signals", {"limit": 5})
    print(f"<- Signaux en attente : {res}")


def main() -> None:
    print("=== BANC D'ESSAI DES CONDITIONS RÉELLES MASCOTTE EKKO ===")
    print("Ce script teste les flux réels du daemon (ingestion, signaux, rejets).")
    print("Pour visualiser le cycle automatique pur des 7 émotions dans l'UI :")
    print("-> Ouvrez DevTools dans l'application Electron (Ctrl+Shift+I)")
    print("-> Exécutez : window.ekkoAPI.cycleAllEmotions()\n")

    if not Path(SOCKET_PATH).exists():
        print(f"[WARN] Daemon non démarré sur {SOCKET_PATH}.")
        sys.exit(1)

    test_error_payload()
    time.sleep(1)
    test_ingesting_and_ready()
    time.sleep(1)
    test_alert_signal()
    print("\n=== FIN DES TESTS DE CHARGE ===")


if __name__ == "__main__":
    main()
