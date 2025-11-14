import argparse
import os
import sys
import subprocess

BASE_DIR = os.path.dirname(__file__)
os.chdir(BASE_DIR)

def run_gui():
    from ui.gui import run_gui as _run
    _run()

def run_text():
    from ui.text_ui import run_text_ui as _run
    _run()

def run_server(host: str = "0.0.0.0", port: int = 5555):
    from network.server import run_server as _run
    _run(host=host, port=port)

def run_client(host: str = None):
    try:
        from network.client import start_client as start_cli
        if host:
            raise ImportError
        start_cli()
    except Exception:
        client_script = os.path.join(BASE_DIR, "network", "client.py")
        cmd = ["python3", client_script]
        if host:
            cmd.append(host)
        subprocess.run(cmd)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BlackJack entrypoint.")
    parser.add_argument("--mode", choices=["gui", "text", "server", "client"], default="gui",
                        help="Which mode to run (default: gui).")
    parser.add_argument("--host", help="Host to bind (server) or connect to (client).")
    parser.add_argument("--port", type=int, default=5555, help="Port for server (default 5555).")
    args = parser.parse_args()

    if args.mode == "gui":
        run_gui()
    elif args.mode == "text":
        run_text()
    elif args.mode == "server":
        run_server(host=(args.host or "0.0.0.0"), port=args.port)
    elif args.mode == "client":
        run_client(host=args.host)