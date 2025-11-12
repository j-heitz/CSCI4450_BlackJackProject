import socket
import threading
from game.blackjack import Round
from game.deck import Deck
from game.player import Player, Dealer

HOST = "localhost"
PORT = 5555

lock = threading.Lock()
clients = {}  # socket -> Player name
players = []
max_players = 2

deck = Deck()
dealer = Dealer()
current_round = None
current_turn_index = 0
game_started = False

def broadcast(message):
    """Send a message to all connected clients."""
    for client in clients:
        try:
            client.sendall(message.encode())
        except:
            pass

def next_player_turn():
    """Advance to the next player's turn, return next Player or None if done."""
    global current_turn_index
    current_turn_index += 1
    while current_turn_index < len(players):
        if not players[current_turn_index].is_busted():
            return players[current_turn_index]
        current_turn_index += 1
    return None

def handle_client(conn, addr):
    global game_started, current_round, current_turn_index

    conn.sendall(b"Welcome to Blackjack! Enter your name: ")
    name = conn.recv(1024).decode().strip()

    with lock:
        if game_started:
            conn.sendall(b"Game already started, please wait for the next round.\n")
            conn.close()
            return

        player = Player(name)
        players.append(player)
        clients[conn] = name

        broadcast(f"{name} joined the game.\n")

        if len(players) == max_players:
            game_started = True
            current_round = Round(deck, players[0], dealer)
            current_round.deal_initial()
            current_turn_index = 0

            broadcast("\nGame started!\n")
            broadcast(show_game_state(hidden=True))
            broadcast(f"\n{players[0].name}'s turn.\n")

    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            command = data.decode().strip().lower()

            with lock:
                if not game_started or current_round is None:
                    conn.sendall(b"Game not started yet.\n")
                    continue

                current_player = players[current_turn_index]
                if clients[conn] != current_player.name:
                    conn.sendall(b"Not your turn.\n")
                    continue

                if command == "hit":
                    current_player.add_card(deck.deal())
                    broadcast(f"{current_player.name} hits!\n")
                    broadcast(show_game_state(hidden=True))

                    if current_player.is_busted():
                        broadcast(f"{current_player.name} busts!\n")
                        next_p = next_player_turn()
                        if next_p:
                            broadcast(f"\n{next_p.name}'s turn.\n")
                        else:
                            end_round()
                            continue
                    else:
                        continue

                elif command == "stand":
                    broadcast(f"{current_player.name} stands.\n")
                    next_p = next_player_turn()
                    if next_p:
                        broadcast(f"\n{next_p.name}'s turn.\n")
                    else:
                        end_round()
                        continue

                elif command == "quit":
                    conn.sendall(b"Goodbye!\n")
                    break

                else:
                    conn.sendall(b"Commands: hit, stand, quit\n")

    except ConnectionResetError:
        pass
    finally:
        with lock:
            if conn in clients:
                left_name = clients.pop(conn)
                broadcast(f"{left_name} left the game.\n")
        conn.close()

def show_game_state(hidden=False):
    """Return a string describing the game state."""
    lines = []
    for p in players:
        lines.append(str(p))
    if hidden and dealer.hand:
        lines.append(f"Dealer: {dealer.hand[0]}, Hidden")
    else:
        lines.append(f"Dealer: " + ", ".join(str(c) for c in dealer.hand) + f" (Value: {dealer.hand_value()})")
    return "\n".join(lines)

def end_round():
    """Dealer plays and results are broadcast."""
    global game_started, current_turn_index
    dealer.play_out(deck)
    results = []

    dv = dealer.hand_value()
    for p in players:
        pv = p.hand_value()
        if p.is_busted():
            results.append(f"{p.name} busts. Dealer wins.")
        elif dealer.is_busted():
            results.append(f"{p.name} wins! Dealer busts.")
        elif pv > dv:
            results.append(f"{p.name} wins!")
        elif pv == dv:
            results.append(f"{p.name} pushes.")
        else:
            results.append(f"{p.name} loses.")

    broadcast("\n--- Final Hands ---\n" + show_game_state(hidden=False))
    broadcast("\n" + "\n".join(results) + "\n")
    broadcast("\nRound over!\n")

    game_started = False
    current_turn_index = 0
    for p in players:
        p.clear_hand()
    dealer.clear_hand()

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Server running on {HOST}:{PORT} ...")

        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()