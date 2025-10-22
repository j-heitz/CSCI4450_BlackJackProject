import socket
import threading
import pickle

SERVER = "localhost"  # or server IP
PORT = 5555

def receive(sock):
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                break
            msg = pickle.loads(data)

            print("\n--- Update ---")
            print(msg.get("message", ""))
            if "dealer_up" in msg:
                print("Dealer shows:", msg["dealer_up"])
            if "dealer_final" in msg:
                print("Dealer final:", ", ".join(msg["dealer_final"]))
            if "players" in msg:
                for name, hand in msg["players"].items():
                    print(f"{name}: {', '.join(hand)}")
            if "current_turn" in msg:
                print(f"\n>>> Current turn: {msg['current_turn']} <<<")
            if "results" in msg:
                print("\n--- Round Results ---")
                for p, r in msg["results"].items():
                    print(f"{p}: {r}")
            print()
        except Exception as e:
            print("Connection lost:", e)
            break

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((SERVER, PORT))
    name = input("Enter your name: ")
    sock.send(name.encode())

    threading.Thread(target=receive, args=(sock,), daemon=True).start()

    while True:
        action = input("Enter action (HIT/STAND/QUIT): ").strip().upper()
        if action == "QUIT":
            break
        sock.send(action.encode())

    sock.close()

if __name__ == "__main__":
    main()