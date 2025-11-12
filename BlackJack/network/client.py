import socket
import threading

HOST = "localhost"
PORT = 5555

def receive_messages(sock):
    while True:
        try:
            data = sock.recv(1024)
            if not data:
                break
            print(data.decode())
        except:
            break

def start_client():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        threading.Thread(target=receive_messages, args=(s,), daemon=True).start()

        while True:
            msg = input()
            if msg.lower() == "quit":
                s.sendall(msg.encode())
                break
            s.sendall(msg.encode())

if __name__ == "__main__":
    start_client()