"""
Boilerplate Competitor Class
----------------------------

Instructions for Participants:
1. Do not import external libraries beyond what's provided.
2. Focus on implementing the `strategy()` method with your trading logic.
3. Use the provided methods to interact with the exchange:
   - self.create_limit_order(price, size, side, symbol) -> order_id if succesfully placed in order book or None
   - self.create_market_order(size, side, symbol) -> order_id if succesfully placed in order book or None
   - self.remove_order(order_id, symbol) -> bool
   - self.get_order_book_snapshot(symbol) -> dict
   - self.get_balance() -> float
   - self.get_portfolio() -> dict

   
Happy Trading!
"""

from typing import Optional, List, Dict
import numpy as np

from Participant import Participant
from utils.internal_ob import InternalOrderBook

class CompetitorBoilerplate(Participant):
    def __init__(self, 
                 participant_id: str,
                 order_book_manager=None,
                 order_queue_manager=None,
                 balance: float = 100000.0):
        """
        Initializes the competitor with default strategy parameters.
        
        :param participant_id: Unique ID for the competitor.
        :param order_book_manager: Reference to the OrderBookManager.
        :param order_queue_manager: Reference to the OrderQueueManager.
        :param balance: Starting balance for the competitor.
        """
        super().__init__(
            participant_id=participant_id,
            balance=balance,
            order_book_manager=order_book_manager,
            order_queue_manager=order_queue_manager
        )

        # Strategy parameters (fixed defaults)
        self.symbols: List[str] = ["NVR", "CPMD", "MFH", "ANG", "TVW"]
        self.book_pressures: Dict[str, List[float]] = {symbol: [] for symbol in self.symbols}
        self.init_balance = balance
        # Create an internal order book for each symbol with an initial price of 1000.00
        self.order_books: Dict[str, InternalOrderBook] = {
            symbol: InternalOrderBook(symbol, 1000.00) for symbol in self.symbols
        }
        
## ONLY EDIT THE CODE BELOW 

    def strategy(self):
        """
        Implement your core trading logic here.
        Now storing book_pressure history, calculating variance using NumPy,
        computing a width based on the current book_pressure and volume,
        and submitting limit orders on both bid and ask sides.
        """
        print(self.get_balance)
        #print(balance)
        #if balance > self.init_balance:
        #   return

        # First, cancel any existing orders from the previous round.
        if hasattr(self, 'last_submitted_order_ids'):
            for symbol, orders in self.last_submitted_order_ids.items():
                if orders.get('bid'):
                    self.remove_order(order_id=orders['bid'], symbol=symbol)
                if orders.get('ask'):
                    self.remove_order(order_id=orders['ask'], symbol=symbol)

        order_ids = {}
        for symbol in self.symbols:
            snapshot = self.get_order_book_snapshot(symbol=symbol)

            # Update the internal order book with the latest snapshot.
            self.order_books[symbol].process_snapshot(snapshot)

            # Grab the best bid/ask levels that exceed a cumulative volume of 20.
            best_bid_price, best_ask_price = self.order_books[symbol].best_levels(
                tolerance_bid=20, tolerance_ask=20
            )

            # Submit limit orders of size 10 at these best price levels.
            bid_order_id = self.create_limit_order(price=best_bid_price, size=10, side='buy', symbol=symbol)
            ask_order_id = self.create_limit_order(price=best_ask_price, size=10, side='sell', symbol=symbol)

            order_ids[symbol] = {'bid': bid_order_id, 'ask': ask_order_id}

        self.last_submitted_order_ids = order_ids
        pass
