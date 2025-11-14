import socket
import threading
import sys

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 5555

def receive_messages(sock):
    while True:
        try:
            data = sock.recv(1024)
            if not data:
                break
            print(data.decode())
        except:
            break

def start_client(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        threading.Thread(target=receive_messages, args=(s,), daemon=True).start()

        while True:
            try:
                msg = input()
            except EOFError:
                break
            if msg.lower() == "quit":
                s.sendall(msg.encode())
                break
            s.sendall(msg.encode())

if __name__ == "__main__":
    # allow calling as: python3 client.py [host] [port]
    host = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PORT
    start_client(host=host, port=port)