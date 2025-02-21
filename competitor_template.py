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
        self.epoch = 0
        
## ONLY EDIT THE CODE BELOW 

    def strategy(self):
        """
        Implement your core trading logic here.
        Now storing book_pressure history, calculating variance using NumPy,
        computing a width based on the current book_pressure and volume,
        and submitting limit orders on both bid and ask sides.
        """
        MIN_EDGE = 0.00
        FADE_RATE = 10**-5 # Fade in percent space per share

        #print(balance)
        #if balance > self.init_balance:
        #   return

        self.epoch += 1
        print(self.epoch)

        port = self.get_portfolio

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

            bid_price = None
            ask_price = None
            bid_vol = None
            ask_vol = None
            
            if bids and asks:
                bid_price, bid_vol = bids[0]
                ask_price, ask_vol = asks[0]


            pos = 0
            if symbol in port:
                pos = port[symbol]

            fair = None
            bid_edge = 0
            ask_edge = 0

            if (bid_price is not None and ask_price is not None):
                mid = (bid_price + ask_price) / 2.0
                fair = mid - pos * mid * FADE_RATE


                bid_edge = fair - bid_price - 0.01
                ask_edge = ask_price - fair - 0.01

            bid_limit_price = None
            ask_limit_price = None
            bid_sz = None
            ask_sz = None

            if (bid_price is not None and bid_edge > MIN_EDGE):
                bid_limit_price = bid_price + 0.01
                bid_sz = np.floor((bid_edge - MIN_EDGE) / (fair * FADE_RATE))
                if bid_sz * bid_limit_price > self.get_balance:
                    bid_sz = np.floor(self.get_balance / bid_limit_price)

            if ask_price is not None and ask_edge > MIN_EDGE:
                ask_limit_price = ask_price - 0.01
                ask_sz = np.floor((ask_edge - MIN_EDGE) / (fair * FADE_RATE))

            if (bid_price > ask_price and bid_vol is not None and ask_vol is not None):
                print("============CROSS============")
                bid_limit_price = ask_price
                ask_limit_price = bid_price
                bid_sz = min(bid_vol, ask_vol)
                if bid_sz * bid_limit_price > self.get_balance:
                    bid_sz = np.floor(self.get_balance / bid_limit_price)

                ask_sz = min(min(ask_vol, bid_vol), bid_sz)

                if (ask_vol > bid_vol and pos < 0):
                    bid_sz = min([bid_vol - pos, ask_vol, np.floor(self.get_balance / bid_limit_price)])
                if (bid_vol > ask_vol and pos > 0):
                    ask_sz = min([ask_vol + pos, bid_vol])


            if bid_limit_price is not None:
                bid_order_id = self.create_limit_order(price=bid_limit_price, size=bid_sz, side='buy', symbol=symbol)
            else:
                bid_order_id = None
            if ask_limit_price is not None:
                ask_order_id = self.create_limit_order(price=ask_limit_price, size=ask_sz, side='sell', symbol=symbol)
            else:
                ask_order_id = None



            order_ids[symbol] = {'bid': bid_order_id, 'ask': ask_order_id}

        self.last_submitted_order_ids = order_ids
        pass
