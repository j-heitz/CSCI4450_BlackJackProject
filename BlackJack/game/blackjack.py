# game/blackjack.py
from game.player import Player, Dealer
from game.deck import Deck

class Round:
    """Encapsulate a single player vs dealer round."""
    def __init__(self, deck: Deck, player: Player, dealer: Dealer = None, hit_on_soft_17: bool = True):
        self.deck = deck
        self.player = player
        self.dealer = dealer or Dealer(hit_on_soft_17=hit_on_soft_17)

    def deal_initial(self):
        self.player.clear_hand()
        self.dealer.clear_hand()
        self.player.add_card(self.deck.deal())
        self.dealer.add_card(self.deck.deal())
        self.player.add_card(self.deck.deal())
        self.dealer.add_card(self.deck.deal())

    def show_dealer_hidden(self):
        if not self.dealer.hand:
            return "Dealer: (no cards)"
        return f"Dealer: {self.dealer.hand[0]}, Hidden"

    def player_turn(self, input_func=input):
        while True:
            if self.player.is_busted():
                return "bust"
            choice = input_func("Hit or Stand? (h/s): ").strip().lower()
            if choice.startswith("h"):
                self.player.add_card(self.deck.deal())
                return "hit"
            if choice.startswith("s"):
                return "stand"

    def dealer_turn(self):
        if not self.player.is_busted():
            self.dealer.play_out(self.deck)

    def determine_winner(self):
        pv = self.player.hand_value()
        dv = self.dealer.hand_value()
        if self.player.is_busted():
            return "Dealer"
        if self.dealer.is_busted():
            return "Player"
        if pv > dv:
            return "Player"
        if dv > pv:
            return "Dealer"
        return "Push"

    def play(self, input_func=input, show_player_fn=print, show_dealer_hidden_fn=lambda d: print(f"Dealer: {d.hand[0]}, Hidden")):
        self.deal_initial()

        if self.player.hand_value() == 21 or self.dealer.hand_value() == 21:
            show_player_fn(self.player)
            print("Dealer (before play):", ", ".join(str(c) for c in self.dealer.hand), f"(Value: {self.dealer.hand_value()})")
            print("\n--- Reveal ---")
            return self.determine_winner()

        player_got_21 = False

        while True:
            show_player_fn(self.player)
            show_dealer_hidden_fn(self.dealer)

            if self.player.is_busted():
                print("You busted!")
                break

            choice = input_func("Hit or Stand? (h/s): ").strip().lower()

            if choice.startswith("h"):
                self.player.add_card(self.deck.deal())

                if self.player.hand_value() == 21:
                    player_got_21 = True
                    print("Player hit 21!")
                    break

                continue
            if choice.startswith("s"):
                break

        print("\n--- Reveal ---")
        show_player_fn(self.player)
        print("Dealer (before play):", ", ".join(str(c) for c in self.dealer.hand), f"(Value: {self.dealer.hand_value()})")

        if not self.player.is_busted() and not player_got_21:
            self.dealer.play_out(self.deck)

        print("Dealer (final):", ", ".join(str(c) for c in self.dealer.hand), f"(Value: {self.dealer.hand_value()})")
        return self.determine_winner()

def evaluate_player_outcome(player, dealer):
    pv = player.hand_value()
    dv = dealer.hand_value()
    if player.is_busted():
        return "LOSE"
    if dealer.is_busted():
        return "WIN"
    if pv > dv:
        return "WIN"
    if pv == dv:
        return "PUSH"
    return "LOSE"

if __name__ == "__main__":
    deck = Deck()
    if hasattr(deck, "shuffle"):
        deck.shuffle()

    player = Player("Player")
    rnd = Round(deck, player, Dealer())

    result = rnd.play()
    if result == "Player":
        print("Player wins!")
    elif result == "Dealer":
        print("Dealer wins!")
    else:
        print("Push (tie).")