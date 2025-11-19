import socket, threading, sys

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 5555

class BlackjackClient:
    def __init__(self):
        self.sock = None
        self._recv_thread = None
        self._on_message = None
        self._lock = threading.Lock()
        self.running = False

    def connect(self, host, port, name, on_message):
        self._on_message = on_message
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.running = True
        self._recv_thread = threading.Thread(target=self._loop, daemon=True)
        self._recv_thread.start()
        self.send(name)

    def _loop(self):
        try:
            while self.running:
                data = self.sock.recv(4096)
                if not data:
                    break
                self._on_message(data.decode(errors="ignore"))
        finally:
            self.running = False

    def send(self, line):
        if not self.running: return
        with self._lock:
            self.sock.sendall((line.strip() + "\n").encode())

    def close(self):
        self.running = False
        try: self.sock.close()
        except: pass

def start_client(host=DEFAULT_HOST, port=DEFAULT_PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        threading.Thread(target=receive_messages, args=(s,), daemon=True).start()
        while True:
            try:
                line = input()
            except EOFError:
                break
            if not line:
                continue
            s.sendall((line + ("\n" if not line.endswith("\n") else "")).encode())
            if line.lower() == "quit":
                break

def receive_messages(sock):
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                break
            print(data.decode(errors="ignore"), end="")
        except:
            break

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PORT
    start_client(host=host, port=port)