import socket
import threading
import pickle
from game.blackjack import Round
from game.player import Player, Dealer
from game.deck import Deck

HOST = '0.0.0.0'
PORT = 5555
MAX_PLAYERS = 1  # set number of players for the table

clients = []
players = []
player_hands = {}
turn_index = 0
game_started = False
lock = threading.Lock()

deck = Deck()
dealer = Dealer()

def send_to_client(conn, data):
    conn.sendall(pickle.dumps(data))

def broadcast(data):
    for c in clients:
        try:
            c.sendall(pickle.dumps(data))
        except:
            pass

def all_players_ready():
    return len(clients) == MAX_PLAYERS

def handle_client(conn, addr):
    global game_started, turn_index

    try:
        name = conn.recv(1024).decode()
        with lock:
            player = Player(name)
            players.append(player)
            clients.append(conn)
            print(f"{name} joined from {addr}")

        send_to_client(conn, {"event": "wait", "message": "Waiting for other players..."})

        # Wait until all players join
        while not all_players_ready():
            if game_started:
                break

        # Start game only once
        with lock:
            if not game_started:
                game_started = True
                start_game()

        # Main message loop
        while True:
            data = conn.recv(1024)
            if not data:
                break

            action = data.decode().strip().lower()

            with lock:
                current_player = players[turn_index]
                if conn != clients[turn_index]:
                    send_to_client(conn, {"event": "not_turn", "message": "It's not your turn!"})
                    continue

                if action.startswith("h"):
                    current_player.add_card(deck.deal())

                    if current_player.is_busted():
                        broadcast_state(f"{current_player.name} busted!")
                        next_turn()
                    else:
                        broadcast_state(f"{current_player.name} hits.")
                elif action.startswith("s"):
                    broadcast_state(f"{current_player.name} stands.")
                    next_turn()

    except Exception as e:
        print(f"Error with {addr}: {e}")
    finally:
        conn.close()

def start_game():
    global player_hands
    broadcast({"event": "start", "message": "All players joined! Dealing cards..."})

    # Deal 2 cards to each player, 2 to dealer
    for player in players:
        player.clear_hand()
        player.add_card(deck.deal())
        player.add_card(deck.deal())
        player_hands[player.name] = player.hand

    dealer.clear_hand()
    dealer.add_card(deck.deal())
    dealer.add_card(deck.deal())

    broadcast_state("Initial deal complete.")
    announce_turn()

def broadcast_state(message):
    """Send all hands and dealer info to everyone."""
    state = {
        "event": "update",
        "message": message,
        "dealer_up": str(dealer.hand[0]),
        "players": {p.name: [str(c) for c in p.hand] for p in players},
        "current_turn": players[turn_index].name if turn_index < len(players) else None
    }
    broadcast(state)

def next_turn():
    global turn_index

    turn_index += 1
    if turn_index >= len(players):
        dealer_turn()
        return
    announce_turn()

def announce_turn():
    broadcast_state(f"It's {players[turn_index].name}'s turn.")

def dealer_turn():
    dealer.play_out(deck)

    results = {}
    for player in players:
        pv = player.hand_value()
        dv = dealer.hand_value()
        if player.is_busted():
            results[player.name] = "Busted — Dealer wins"
        elif dealer.is_busted():
            results[player.name] = "Dealer busts — Player wins"
        elif pv > dv:
            results[player.name] = "Player wins"
        elif dv > pv:
            results[player.name] = "Dealer wins"
        else:
            results[player.name] = "Push (tie)"

    broadcast({
        "event": "results",
        "message": "Dealer plays out.",
        "dealer_final": [str(c) for c in dealer.hand],
        "results": results
    })

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"Server running on {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        thread.start()

if __name__ == "__main__":
    main()