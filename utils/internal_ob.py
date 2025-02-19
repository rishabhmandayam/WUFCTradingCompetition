import numpy as np

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
            level = int(round(price * self.scale))
            if level > new_max_level:
                new_max_level = level
        for price, volume in asks_snapshot:
            level = int(round(price * self.scale))
            if level > new_max_level:
                new_max_level = level

        # Resize arrays if necessary
        if new_max_level > self.max_level:
            self.resize(new_max_level)

        self.bids.fill(0)
        self.asks.fill(0)

        # Populate the bids side (each level index directly maps to price * scale)
        for price, volume in bids_snapshot:
            level = int(round(price * self.scale))
            self.bids[level] = volume

        # Populate the asks side
        for price, volume in asks_snapshot:
            level = int(round(price * self.scale))
            self.asks[level] = volume

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
        
        Note: For bids we iterate from high to low and for asks from low to high,
              adjusting the level by +1 (for bids) and -1 (for asks) as in your original
              method. Values are clamped within [0, max_level].
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
