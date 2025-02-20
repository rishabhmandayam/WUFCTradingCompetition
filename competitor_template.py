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
import math

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
    def normal_cdf(self, x, loc=0, scale=1):
        return 0.5 * (1 + math.erf((x - loc) / (scale * math.sqrt(2))))

    def get_size(self, best_levels, fair_value, global_sigma, alpha, delta):
        bid, ask = best_levels
        score_bid = 1 - self.normal_cdf(bid, loc=fair_value, scale=global_sigma)
        score_ask = self.normal_cdf(ask, loc=fair_value, scale=global_sigma)
        size_bid = alpha * np.tanh(delta * (score_bid - 0.5))
        size_ask = alpha * np.tanh(delta * (score_ask - 0.5))
        output = {"Bid": {"Size": size_bid, "Level": bid},
                "Ask": {"Size": size_ask, "Level": ask},
                "Fair Value": fair_value}
        return output

    def strategy(self):
        """
        Implement your core trading logic here.
        Now storing book_pressure history, calculating variance using NumPy,
        computing a width based on the current book_pressure and volume,
        and submitting limit orders on both bid and ask sides.
        """
        portfolio = self.get_portfolio
        print(portfolio)

        # Cancel existing orders
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
                book_pressure = (bid_price * ask_vol + ask_price * bid_vol) / total_vol if total_vol else None
            else:
                book_pressure = None
                total_vol = 0

            if book_pressure is not None:
                self.book_pressures[symbol].append(book_pressure)
            
            arr = np.array(self.book_pressures[symbol])
            if arr.size > 1:
                variance = np.var(arr)
                stdev = np.sqrt(variance)
                
            else:
                variance = 0.0
                stdev = 0.0

            # Update the internal order book with the latest snapshot.
            self.order_books[symbol].process_snapshot(snapshot)

            # Grab the best bid/ask levels that exceed a cumulative volume of 10.
            best_levels = self.order_books[symbol].best_levels(
                tolerance_bid=10, tolerance_ask=10
            )

            if best_levels and stdev > 0:
                risk_nuetral_trades = self.get_size(best_levels=best_levels, fair_value=book_pressure, global_sigma=stdev, alpha=10, delta=0.8)
                position = portfolio.get(symbol, None)
                if position is not None:
                    pos_variance = (position ** 2) * variance
                    partial = 2 * position * variance
                else:
                    pos_variance = 0
                    partial = 0

                kappa = 0.0008
                old_bid_size = risk_nuetral_trades["Bid"]["Size"]
                new_bid_size = round(old_bid_size * np.exp(-1 * kappa * pos_variance * partial), 0)

                old_ask_size = risk_nuetral_trades["Ask"]["Size"]
                new_ask_size = round(old_ask_size * np.exp(kappa * pos_variance * partial), 0) 
                
                bid_order_id = self.create_limit_order(
                    price=risk_nuetral_trades["Bid"]["Level"],
                    size=new_bid_size,
                    side='buy',
                    symbol=symbol
                )
                ask_order_id = self.create_limit_order(
                    price=risk_nuetral_trades["Ask"]["Level"],
                    size=new_ask_size,
                    side='sell',
                    symbol=symbol
                )
                order_ids[symbol] = {'bid': bid_order_id, 'ask': ask_order_id}

        self.last_submitted_order_ids = order_ids
        pass
