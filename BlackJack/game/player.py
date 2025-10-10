# game/player.py
from game.deck import Card

class Player:
    def __init__(self, name, chips=1000):
        self.name = name
        self.chips = chips
        self.hand = []
        self.bet = 0

    def add_card(self, card: Card):
        """Add a dealt card to the player's hand."""
        self.hand.append(card)

    def clear_hand(self):
        """Empty the player's hand and reset bet."""
        self.hand = []
        self.bet = 0

    def place_bet(self, amount):
        """Deduct chips and set current bet."""
        if amount > self.chips:
            raise ValueError(f"{self.name} does not have enough chips!")
        self.chips -= amount
        self.bet = amount

    def hand_value(self):
        """Return the total blackjack value of the hand."""
        value = sum(card.value for card in self.hand)
        aces = sum(1 for card in self.hand if card.rank == "A")

        while value > 21 and aces:
            value -= 10
            aces -= 1

        return value

    def is_busted(self):
        return self.hand_value() > 21

    def __str__(self):
        cards = ", ".join(str(card) for card in self.hand)
        return f"{self.name}: {cards} (Value: {self.hand_value()})"


class Dealer(Player):
    def __init__(self, hit_on_soft_17=True):
        super().__init__("Dealer")

        self.hit_on_soft_17 = hit_on_soft_17

    def _is_soft(self):
        """Return True if the hand is a soft total (an Ace can count as 11)."""
        aces = sum(1 for c in self.hand if c.rank == "A")
        if not aces:
            return False

        min_value = sum((1 if c.rank == "A" else c.value) for c in self.hand)

        return min_value + 10 <= 21

    def should_hit(self):
        """Dealer hits until reaching a hand value of 17 or more.
        Optionally hits on soft 17 when hit_on_soft_17 is True.
        """
        val = self.hand_value()
        if val < 17:
            return True
        if val == 17 and self._is_soft() and self.hit_on_soft_17:
            return True
        return False

    def play_out(self, deck):
        """Draw from deck until dealer should stand."""
       
        while len(self.hand) < 2:
            self.add_card(deck.deal())

        while self.should_hit():
            self.add_card(deck.deal())
    