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

class InternalOrderBook:
    """
    A class to maintain an order book for bids and asks safely.
    It processes snapshots as per the schema, using numpy arrays to track volume at fixed price levels.

    Prices are stored as integer "levels" using a scale factor. For instance, an incoming
    price of 17.22 is converted to 1722. The valid price levels range from 0 up to
    init_price * 4 (after scaling). If a snapshot comes with a price exceeding the current
    range the underlying arrays are resized accordingly.
    """

    def __init__(self, market_ticker, init_price):
        self.market_ticker = market_ticker
        self.scale = 100  # conversion factor: 1 unit of price equals 100 in our level system
        self.max_level = int(init_price * 4 * self.scale)
        self.bids = np.zeros(self.max_level + 1, dtype=int)
        self.asks = np.zeros(self.max_level + 1, dtype=int)
        self.last_seq = None  # for later use if needed

    def resize(self, new_max_level):
        """
        Resize the underlying order book arrays when incoming snapshot data
        includes price levels above the current max_level.
        """
        new_bids = np.zeros(new_max_level + 1, dtype=int)
        new_asks = np.zeros(new_max_level + 1, dtype=int)
        # Copy existing data into the new arrays
        new_bids[:self.max_level + 1] = self.bids
        new_asks[:self.max_level + 1] = self.asks
        self.bids = new_bids
        self.asks = new_asks
        self.max_level = new_max_level

    def process_snapshot(self, snapshot):
        """
        Process a snapshot that is expected to be in the form:

            {
             "bids": [(price, volume), ...],
             "asks": [(price, volume), ...]
            }

        Prices are provided as floats (e.g., 17.22) and are converted to levels (e.g., 1722).
        If any price level in the snapshot exceeds the order book's current range,
        the underlying arrays are dynamically resized.
        """
        bids_snapshot = snapshot.get("bids", [])
        asks_snapshot = snapshot.get("asks", [])

        # Determine the maximum price level in the snapshot (after conversion)
        new_max_level = self.max_level
        for price, volume in bids_snapshot:
            level = min(int(round(price * self.scale)), 100000)
            if level > new_max_level:
                new_max_level = level
        for price, volume in asks_snapshot:
            level = min(int(round(price * self.scale)), 100000)
            if level > new_max_level:
                new_max_level = level

        # Resize arrays if necessary
        if new_max_level > self.max_level:
            self.resize(new_max_level)

        self.bids.fill(0)
        self.asks.fill(0)

        # Populate the bids side (each level index directly maps to price * scale)
        for price, volume in bids_snapshot:
            level = min(int(round(price * self.scale)), 100000)
            self.bids[level] = min(volume, 100000)
            if (volume > 100000):
                print("HIGH VOLUME ERROR", price, volume, "BID")

        # Populate the asks side
        for price, volume in asks_snapshot:
            level = min(int(round(price * self.scale)), 100000)
            self.asks[level] = min(volume, 100000)
            if (volume > 100000):
                print("HIGH VOLUME ERROR", price, volume, "ASK")

    def best_bid(self):
        """
        Returns the best bid as a tuple (price, volume).
        The best bid is the highest price level (largest level index) with non-zero volume.
        Price is returned as a float.
        """
        for level in range(self.max_level, -1, -1):
            if self.bids[level] > 0:
                return level / self.scale, int(self.bids[level])
        return 0, 0

    def best_ask(self):
        """
        Returns the best ask as a tuple (price, volume).
        The best ask is the lowest price level (smallest level index) with non-zero volume.
        Price is returned as a float.
        """
        for level in range(0, self.max_level + 1):
            if self.asks[level] > 0:
                return level / self.scale, int(self.asks[level])
        # If no asks, return the highest possible price from this book.
        return self.max_level / self.scale, 0

    def best_levels(self, tolerance_bid, tolerance_ask):
        """
        Finds the best bid and ask levels where the cumulative volume
        first exceeds the tolerance. This can be used to gauge order depth.

        Parameters:
            tolerance_bid (int): Maximum cumulative volume allowed ahead on the bid side.
            tolerance_ask (int): Maximum cumulative volume allowed ahead on the ask side.

        Returns:
            A tuple (best_bid_price, best_ask_price) with prices as floats.
        """
        cumulative_bid = 0
        best_bid_level = 0
        for level in range(self.max_level, -1, -1):
            cumulative_bid += self.bids[level]
            if cumulative_bid > tolerance_bid:
                best_bid_level = min(level + 1, self.max_level)
                break

        cumulative_ask = 0
        best_ask_level = self.max_level
        for level in range(0, self.max_level + 1):
            cumulative_ask += self.asks[level]
            if cumulative_ask > tolerance_ask:
                best_ask_level = max(level - 1, 0)
                break

        return best_bid_level / self.scale, best_ask_level / self.scale

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
            order_queue_manager=order_queue_manager,
        )

        # Strategy parameters (fixed defaults)
        self.symbols: List[str] = ["NVR", "CPMD", "MFH", "ANG", "TVW"]
        self.book_pressures: Dict[str, List[float]] = {symbol: [] for symbol in self.symbols}
        self.init_balance = balance
        # Create an internal order book for each symbol with an initial price of 1000.00
        self.order_books: Dict[str, InternalOrderBook] = {
            symbol: InternalOrderBook(symbol, 1000.00) for symbol in self.symbols
        }
        self.epoch = 0

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

        self.epoch += 1

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

            bid_price = None
            bid_vol = None
            ask_price = None
            ask_vol = None

            pos = 0
            if symbol in portfolio:
                pos = portfolio[symbol]

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
                tolerance_bid=250, tolerance_ask=250
            )

            if (self.epoch % 2 == 0 and bid_price is not None and ask_price is not None and bid_price > ask_price and bid_vol is not None and ask_vol is not None):
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

                bid_order_id = self.create_limit_order(
                    price=bid_limit_price,
                    size=bid_sz,
                    side='buy',
                    symbol=symbol
                )
                ask_order_id = self.create_limit_order(
                    price=ask_limit_price,
                    size=ask_sz,
                    side='sell',
                    symbol=symbol
                )
                order_ids[symbol] = {'bid': bid_order_id, 'ask': ask_order_id}



            elif book_pressure and best_levels and stdev > 0:
                risk_nuetral_trades = self.get_size(best_levels=best_levels, fair_value=book_pressure, global_sigma=stdev, alpha=2500, delta=0.2)
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

                if new_bid_size > self.get_balance / risk_nuetral_trades["Bid"]["Level"]:
                    new_bid_size = np.floor(self.get_balance / risk_nuetral_trades["Bid"]["Level"])

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
#%%
