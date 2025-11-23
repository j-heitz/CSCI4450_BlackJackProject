import socket, threading, time
from game.deck import Deck
from game.player import Player, Dealer
from game.blackjack import evaluate_player_outcome
from game.blackjack import Round

HOST = "0.0.0.0"
PORT = 5555

lock = threading.Lock()
join_countdown_lock = threading.Lock()
clients = {}
players = []
waiting_players = []
max_players = 5

deck = Deck()
dealer = Dealer()
game_started = False
current_turn_index = -1
rounds_played = 0

join_countdown_event = None
between_countdown_event = None

def broadcast(msg: str):
    dead = []
    for c in list(clients.keys()):
        try:
            c.sendall(msg.encode())
        except:
            dead.append(c)
    for d in dead:
        try: d.close()
        except: pass
        p = clients.pop(d, None)
        if p and p in players:
            players.remove(p)

def push_state(hidden=True):
    lines = []
    for p in players:
        hand_txt = ", ".join(str(c) for c in p.hand)
        lines.append(f"STATE: PLAYER {p.name} | {hand_txt} | VALUE={p.hand_value()}")
    if hidden:
        if dealer.hand:
            lines.append(f"STATE: DEALER HIDDEN | {dealer.hand[0]}")
        else:
            lines.append("STATE: DEALER HIDDEN | (no card)")
    else:
        d_txt = ", ".join(str(c) for c in dealer.hand)
        lines.append(f"STATE: DEALER Dealer | {d_txt} | VALUE={dealer.hand_value()}")
    broadcast("\n".join(lines) + "\n")

def start_join_countdown(seconds=10):
    global join_countdown_event
    with join_countdown_lock:
        if game_started or not players or rounds_played > 0 or join_countdown_event:
            return
        join_countdown_event = threading.Event()

    def run():
        for s in range(seconds, 0, -1):
            if join_countdown_event.is_set(): return
            broadcast(f"GAME_COUNTDOWN {s}\n")
            time.sleep(1)
        if join_countdown_event.is_set(): return
        broadcast("GAME_START\n")
        start_round()

    threading.Thread(target=run, daemon=True).start()

def start_between_round_countdown(seconds=8):
    global between_countdown_event
    with join_countdown_lock:
        if game_started or not players or between_countdown_event:
            return
        between_countdown_event = threading.Event()

    def run():
        for s in range(seconds, 0, -1):
            if between_countdown_event.is_set(): return
            broadcast(f"GAME_COUNTDOWN {s}\n")
            time.sleep(1)
        if between_countdown_event.is_set(): return
        broadcast("GAME_START\n")
        start_round()

    threading.Thread(target=run, daemon=True).start()

def cancel_countdowns():
    global join_countdown_event, between_countdown_event
    if join_countdown_event: join_countdown_event.set(); join_countdown_event = None
    if between_countdown_event: between_countdown_event.set(); between_countdown_event = None

def start_round():
    global deck, dealer, current_turn_index, game_started, rounds_played
    with lock:
        cancel_countdowns()
        if not players:
            return
        game_started = True
        rounds_played += 1
        deck = Deck()
        if hasattr(deck, "shuffle"): deck.shuffle()
        dealer.clear_hand()
        for p in players: p.clear_hand()
        for _ in range(2):
            for p in players:
                p.add_card(deck.deal())
            dealer.add_card(deck.deal())
        broadcast("ROUND_START\n")
        push_state(hidden=True)
        dealer_blackjack = dealer.hand_value() == 21
        player_blackjacks = any(p.hand_value() == 21 for p in players)
        if dealer_blackjack or player_blackjacks:
            push_state(hidden=False)
            resolve_round(immediate=True)
            return
        current_turn_index = 0
        broadcast(f"TURN: {players[0].name}\n")

def next_turn():
    global current_turn_index, game_started
    with lock:
        if not game_started: return
        current_turn_index += 1
        if current_turn_index >= len(players):
            broadcast("TURN: Dealer\n")
            dealer_play()
            return
        broadcast(f"TURN: {players[current_turn_index].name}\n")

def dealer_play():
    broadcast("TURN: Dealer\n")
    try:
        while dealer.should_hit():
            dealer.add_card(deck.deal())
            broadcast(f"ACTION: DEALER_HIT {dealer.hand[-1]}\n")
    except Exception as e:
        broadcast(f"SERVER_ERROR DealerPlay {type(e).__name__}: {e}\n")
    push_state(hidden=False)
    resolve_round(immediate=False)


def resolve_round(immediate=False):
    global game_started
    winners, pushes, losers = [], [], []
    for p in players:
        outcome = evaluate_player_outcome(p, dealer)
        if outcome == "WIN": winners.append(p.name)
        elif outcome == "PUSH": pushes.append(p.name)
        else: losers.append(p.name)
        broadcast(f"RESULT: {p.name} {outcome}\n")
    broadcast(f"RESULT_SUMMARY: WINNERS={','.join(winners) or '-'} PUSHES={','.join(pushes) or '-'} LOSERS={','.join(losers) or '-'}\n")
    broadcast("ROUND_END\n")
    game_started = False
    for p in players: p.clear_hand()
    dealer.clear_hand()

    while waiting_players and len(players) < max_players:
        np = waiting_players.pop(0)
        players.append(np)
        broadcast(f"EVENT: JOIN {np.name}\n")
    if players:
        start_between_round_countdown()

def handle_action(player: Player, line: str, pingConn):
    cmd = line.strip().upper()
    if cmd == "PING":
        pingConn.sendall(b"PING\n")
        return
    if not game_started: return
    if players[current_turn_index] != player:
        return
    if cmd == "HIT":
        card = deck.deal()
        player.add_card(card)
        broadcast(f"ACTION: HIT {player.name} {card}\n")
        push_state(hidden=True)
        if player.hand_value() == 21:
            broadcast(f"ACTION: BLACKJACK {player.name}\n")
            next_turn()
        if player.hand_value() > 21:
            broadcast(f"ACTION: BUST {player.name}\n")
            next_turn()
        return
    if cmd == "STAND":
        broadcast(f"ACTION: STAND {player.name}\n")
        next_turn()
        return



def remove_player(p: Player):
    if p in players:
        players.remove(p)
    if p in waiting_players:
        waiting_players.remove(p)

def handle_client(conn):
    try:
        name = conn.recv(128).decode().strip()
        if not name:
            name = f"Player{len(clients)+1}"
        with lock:
            pl = Player(name)
            clients[conn] = pl
            if game_started:
                waiting_players.append(pl)
                conn.sendall(b"Round in progress. You will join next round.\n")
                broadcast(f"EVENT: JOIN_WAIT {name}\n")
            else:
                players.append(pl)
                broadcast(f"EVENT: JOIN {name}\n")
                push_state(hidden=not game_started)
                if rounds_played == 0:
                    start_join_countdown()

        while True:
            data = conn.recv(256)
            if not data:
                break
            for line in data.decode().splitlines():
                if line.lower() == "quit":
                    raise ConnectionError()
                handle_action(pl, line, conn)
    except:
        pass
    finally:
        with lock:
            p = clients.pop(conn, None)
            if p:
                remove_player(p)
                broadcast(f"EVENT: LEAVE {p.name}\n")
            if not game_started and players:
                if rounds_played == 0 and not join_countdown_event:
                    start_join_countdown()
        try: conn.close()
        except: pass

def run_server(host=HOST, port=PORT):
    print(f"Server on {host}:{port}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen()
        while True:
            c, a = s.accept()
            threading.Thread(target=handle_client, args=(c,), daemon=True).start()

if __name__ == "__main__":
    run_server()