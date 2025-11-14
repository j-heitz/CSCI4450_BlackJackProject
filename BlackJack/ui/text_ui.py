from game.blackjack import Round
from game.player import Player, Dealer
from game.deck import Deck

def run_text_ui():
    """Run the text-based blackjack game."""
    print("=" * 40)
    print("Welcome to Blackjack (Text Mode)")
    print("=" * 40)

    while True:
        deck = Deck()
        if hasattr(deck, "shuffle"):
            deck.shuffle()

        player = Player("Player")
        rnd = Round(deck, player, Dealer())

        result = rnd.play()

        print("\n" + "-" * 40)
        if result == "Player":
            print("Player wins!")
        elif result == "Dealer":
            print("Dealer wins!")
        else:
            print("Push (tie).")
        print("-" * 40)

        again = input("Play again? (y/n): ").strip().lower()
        if not again.startswith("y"):
            print("Goodbye.")
            break

if __name__ == "__main__":
    run_text_ui()