from limitTreeNodes import LimitLevelTree
from limitTreeNodes import LimitLevel
import traceback

class LimitOrderBook:
    """Limit Order Book (LOB) implementation for High Frequency Trading."""

    def __init__(self, symbol: str):
        self.bids = LimitLevelTree()      # AVL tree for bids
        self.asks = LimitLevelTree()      # AVL tree for asks
        self.best_bid = None             # Points to the LimitLevel node with highest price
        self.best_ask = None             # Points to the LimitLevel node with lowest price

        # Instead of { price -> LimitLevel }, we do { (price, is_bid) -> LimitLevel }
        self._price_levels = {}

        # Track all orders by their ID
        self._orders = {}
        self.symbol = symbol
        self.hasProcessed = 0

    # ------------------------------------------------------------------------
    # Top-level queries
    # ------------------------------------------------------------------------
    def top_level(self, askForBid: bool):
        """
        Returns the best available order (i.e., head of the best LimitLevel's queue)
        for bids or asks.
        """
        if askForBid:
            return self.best_bid.orders.head if self.best_bid is not None else None
        else:
            return self.best_ask.orders.head if self.best_ask is not None else None

    def get_best_price(self, askForBid: bool):
        """
        Returns the best bid or ask price.
        """
        if askForBid:
            return self.best_bid.price if self.best_bid else None
        else:
            return self.best_ask.price if self.best_ask else None

    # ------------------------------------------------------------------------
    # Main "process" method (add / remove / update)
    # ------------------------------------------------------------------------
    def process(self, order, quantity: int):
        """
        Processes the given order:
          - Remove it if size == 0
          - Update it if it exists
          - Add it otherwise
        """
        if order.size == 0:
            self.remove(order)
        else:
            if order.order_id in self._orders:
                self.update(order, quantity)
            else:
                self.add(order)


    def update(self, order, size_diff):
        """
        Updates an existing order in the book's internal structures.
        Adjust the parent limit's size by size_diff.
        """
        # Update the in-memory order
        self._orders[order.order_id].size = order.size
        # Decrement the parent's total size
        self._orders[order.order_id].parent_limit.size -= size_diff

    def remove(self, order):
        """
        Removes an order from the order book. If that LimitLevel becomes empty,
        remove the node from the relevant tree and possibly update best_bid/best_ask.
        """
        try:
            popped_item = self._orders.pop(order.order_id)
        except KeyError:
            # The order wasn't in the book anyway
            return False

        # Remove from the doubly-linked list at that price level
        popped_item.pop_from_list()

        # Now check if that was the last order at that (price, is_bid) level
        level_key = (popped_item.price, popped_item.is_bid)
        try:
            if len(self._price_levels[level_key]) == 0:
                # Remove the entire LimitLevel from the dictionary
                popped_limit_level = self._price_levels.pop(level_key)

                # Remove from the AVL tree
                popped_limit_level.remove()

                # If that price level was the best for that side, re-derive best bid/ask
                if popped_item.is_bid:
                    if popped_limit_level == self.best_bid:
                        self._update_best_bid()
                else:
                    if popped_limit_level == self.best_ask:
                        self._update_best_ask()

        except KeyError as e:
            print("Error removing price level from dictionary", e)
            traceback.print_exc()
            pass

    def add(self, order):
        """
        Adds a new order to the book. If the (price, is_bid) level doesn't exist yet,
        create a new LimitLevel and insert it into the relevant tree. Otherwise, append.
        """
        level_key = (order.price, order.is_bid)
        already_in_dict = level_key in self._price_levels

        try:
            if not already_in_dict:
                # Create a new LimitLevel
                limit_level = LimitLevel(order)
                # Store this order in the global _orders dict
                self._orders[order.order_id] = order
                # And store the limit level under (price, is_bid)
                self._price_levels[level_key] = limit_level

                # Insert into the appropriate AVL tree
                if order.is_bid:
                    self.bids.insert(limit_level)
                    # Possibly update best_bid
                    if (self.best_bid is None) or (limit_level.price > self.best_bid.price):
                        self.best_bid = limit_level
                else:
                    self.asks.insert(limit_level)
                    # Possibly update best_ask
                    if (self.best_ask is None) or (limit_level.price < self.best_ask.price):
                        self.best_ask = limit_level

            else:
                # We already have a LimitLevel for this (price, side)
                self._orders[order.order_id] = order
                self._price_levels[level_key].append(order)

        except Exception as e:
            # If something went wrong after we determined "already_in_dict"
            if already_in_dict:
                print("Exception while adding order to existing level:", e)
            else:
                # If we created a new node but failed somehow
                self._orders[order.order_id] = order
                self._price_levels[level_key].append(order)

    # ------------------------------------------------------------------------
    # Best Bid/Ask Recalculation
    # ------------------------------------------------------------------------
    def _update_best_bid(self):
        """Walk the bids AVL tree to find the node with the maximum price."""
        if self.bids.right_child is None:
            self.best_bid = None
            return None

        node = self.bids.right_child
        while node.right_child:
            node = node.right_child
        self.best_bid = node
        return self.best_bid.orders.head

    def _update_best_ask(self):
        """Walk the asks AVL tree to find the node with the minimum price."""
        if self.asks.right_child is None:
            self.best_ask = None
            return None

        node = self.asks.right_child
        while node.left_child:
            node = node.left_child
        self.best_ask = node
        return self.best_ask.orders.head

    # ------------------------------------------------------------------------
    # Utility: Dump the order book 
    # ------------------------------------------------------------------------
    def get_order_book(self, depth=None):
        """
        Returns the price levels as a dict: {
            'bids': [(price, size), ...],
            'asks': [(price, size), ...]
        }, up to `depth` levels if provided.
        
        We gather all unique prices from the dictionary keys, separate them
        into bids vs asks, and then sort accordingly.
        """
        # Separate bid keys vs ask keys
        try: 
            bid_keys = []
            ask_keys = []
            for (price, is_bid) in self._price_levels.keys():
                if is_bid:
                    bid_keys.append(price)
                else:
                    ask_keys.append(price)

            # Sort bids descending, asks ascending
            bid_keys.sort(reverse=True)
            ask_keys.sort()

            # Build (price, total size) lists
            # We'll filter by best_ask_price, best_bid_price in the same way you had
            best_bid_price = self.best_bid.price if self.best_bid else float('-inf')
            best_ask_price = self.best_ask.price if self.best_ask else float('inf')

            # Bids: only those < best_ask_price (from your old code)
            bids_all = [
                (float(price), self._price_levels[(price, True)].size)
                for price in bid_keys
                if price < best_ask_price and (price, True) in self._price_levels
            ]
            if depth is not None:
                bids_all = bids_all[:depth]

            # Asks: only those > best_bid_price
            asks_all = [
                (float(price), self._price_levels[(price, False)].size)
                for price in ask_keys
                if price > best_bid_price and (price, False) in self._price_levels
            ]
            if depth is not None:
                asks_all = asks_all[:depth]

            return {
                'bids': bids_all,
                'asks': asks_all,
            }
        except Exception:
            return {
                'bids': [],
                'asks': [],
            }
