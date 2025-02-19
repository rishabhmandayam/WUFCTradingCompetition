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

from Participant import Participant

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
        
## ONLY EDIT THE CODE BELOW 

    def strategy(self):
        """
        Implement your core trading logic here.
        Now storing book_pressure history, calculating variance,
        computing a width based on the current book_pressure and volume,
        and submitting limit orders on both bid and ask sides.
        """

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
            bids = snapshot.get('bids', [])
            asks = snapshot.get('asks', [])
            
            if bids and asks:
                bid_price, bid_vol = bids[0]
                ask_price, ask_vol = asks[0]
                total_vol = bid_vol + ask_vol
                book_pressure = (bid_price * bid_vol + ask_price * ask_vol) / total_vol if total_vol else None
            else:
                book_pressure = None
                total_vol = 0

            if book_pressure is not None:
                self.book_pressures[symbol].append(book_pressure)
            
            #vol calculations
            if len(self.book_pressures[symbol]) > 1:
                mean_bp = sum(self.book_pressures[symbol]) / len(self.book_pressures[symbol])
                variance = sum((bp - mean_bp) ** 2 for bp in self.book_pressures[symbol]) / len(self.book_pressures[symbol])
                stdev = variance ** 0.5 
            else:
                variance = 0.0
                stdev = 0.0  

            width = stdev

            bid_limit_price = book_pressure - width if book_pressure is not None else None
            ask_limit_price = book_pressure + width if book_pressure is not None else None

            if bid_limit_price is not None:
                bid_order_id = self.create_limit_order(price=bid_limit_price, size=10, side='buy', symbol=symbol)
            else:
                bid_order_id = None
            if ask_limit_price is not None:
                ask_order_id = self.create_limit_order(price=ask_limit_price, size=10, side='sell', symbol=symbol)
            else:
                ask_order_id = None

            order_ids[symbol] = {'bid': bid_order_id, 'ask': ask_order_id}

        self.last_submitted_order_ids = order_ids
        pass
