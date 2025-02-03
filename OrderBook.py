# order_book.py

import heapq
from enum import Enum
import threading
from typing import List, Tuple, Union
from Order import Order
import time

from Participant import Participant
from ParticipantManager import ParticipantManager


class MatchResult(Enum):
    SUCCESS = "success"
    SELF_TRADE_ERROR = "self_trade_error"
    PRICE_MISMATCH_ERROR = "price_mismatch_error"
    INSUFFICIENT_BALANCE_ERROR = "insufficient_balance_error"


class OrderBook:
    def __init__(self, symbol: str, pm: ParticipantManager):
        
        self.bids: List[Order] = []  # Max-heap for buy orders
        
        self.asks: List[Order] = []  # Min-heap for sell orders

        self.pm = pm
        self.symbol = symbol
        self.order_map = {}
        # No lock needed now since all operations are single-threaded

    def add_order(self, order: Order):
        order.price = round(order.price, 2)
        if order.side == 'buy':
            heapq.heappush(self.bids, order)
            order.orderLife = "INORDERBOOK"
            personPlacingOrder = order.participant_id
            if not self.pm.contains_participant(personPlacingOrder):
                self.pm.add_participant(Participant(personPlacingOrder))
        elif order.side == 'sell':
            heapq.heappush(self.asks, order)
            order.orderLife = "INORDERBOOK"
            personPlacingOrder = order.participant_id
            if not self.pm.contains_participant(personPlacingOrder):
                self.pm.add_participant(Participant(personPlacingOrder))
        else:
            raise ValueError("Order side must be 'buy' or 'sell'.")
        self.order_map[order.order_id] = order
        return True

        # check buyer balance
        # go through the asks/bids heapq (depending on if it is a market sell order or market buy order)
        # for each order, if it is a buy order, if it is less than the order quantity and the buyer can afford it, then fill the order and move to the next
        # if it is a sell order, if it is less than the order quantitiy fill the order, send the pm the recieve order about the details, and get the next one of the heapq and keep filling
        # keep filling until we have filled the order quantity or the buy can no longer afford more, then add back the rest of the partially filled order back to the heapq
        # return True

    def accept_market_order(self, order: Order) -> bool:
        """
        Processes a market order by matching it against the opposite side's
        limit orders (or any orders) in the order book. Fills the market order
        partially or fully until:
        - The entire market order quantity is filled, or
        - The buyer cannot afford more, or
        - No more matching orders are available.

        Returns True if any part of the order was filled, False otherwise.
        """
        if order.side == 'buy':
            # We'll match a BUY market order against the existing SELL orders (self.asks).
            opposite_heap = self.asks
        elif order.side == 'sell':
            # We'll match a SELL market order against the existing BUY orders (self.bids).
            opposite_heap = self.bids
        else:
            raise ValueError("Order side must be 'buy' or 'sell'.")

        # If no orders are available to match, return False immediately.
        if not opposite_heap:
            return False

       
        order_filled = False

        # Continuously attempt to match until the order is filled or no more orders are available
        while order.quantity > 0 and opposite_heap:
            best_opposite_order = heapq.heappop(opposite_heap)  # Get the best (lowest ask or highest bid)

            # Determine trade price (market order typically trades at the price of the resting order)
            trade_price = best_opposite_order.price
            if trade_price is None:
                # If the resting order also has no price (e.g., it was itself a market order),
                raise ValueError("matched with a market order")

            trade_quantity = min(order.quantity, best_opposite_order.quantity)
            total_cost = trade_price * trade_quantity

            if order.side == 'buy':
                # Check if buyer can afford it
                buyer_balance = self.pm.get_participant_balance(order.participant_id)
                if buyer_balance < total_cost:
                    # Attempt partial fill based on available balance
                    partial_quantity = int(buyer_balance // trade_price)
                    if partial_quantity <= 0:
                        # The buyer cannot afford even 1 unit at this price; re-insert the order and stop.
                        heapq.heappush(opposite_heap, best_opposite_order)
                        break
                    trade_quantity = partial_quantity
                    total_cost = trade_price * trade_quantity
            else:
                # side == 'sell'
                # A SELL market order does not require a balance check for the seller,
                # because the seller only needs to have enough quantity (already in 'order.quantity')
                pass

            # If after partial calculation trade_quantity is 0, break.
            if trade_quantity <= 0:
                heapq.heappush(opposite_heap, best_opposite_order)
                break

            # We have a valid trade now
            # Decrease the buyer's or seller's quantity
            # Decrease the resting order's quantity
            best_opposite_order.quantity -= trade_quantity
            order.quantity -= trade_quantity
            order_filled = True  # We have at least partially filled this market order

            # Send execution reports
            if order.side == 'buy':
                # buyer = order.participant_id
                # seller = best_opposite_order.participant_id
                self.pm.send_execution_report(
                    buyer_participant_id=order.participant_id,
                    seller_participant_id=best_opposite_order.participant_id,
                    trade_details={
                        'buyer_order_id': order.order_id,
                        'seller_order_id': best_opposite_order.order_id,
                        'symbol': order.symbol,  # Both should match
                        'price': trade_price,
                        'quantity': trade_quantity
                    }
                )
            else:
                # side == 'sell'
                # buyer = best_opposite_order.participant_id
                # seller = order.participant_id
                self.pm.send_execution_report(
                    buyer_participant_id=best_opposite_order.participant_id,
                    seller_participant_id=order.participant_id,
                    trade_details={
                        'buyer_order_id': best_opposite_order.order_id,
                        'seller_order_id': order.order_id,
                        'symbol': order.symbol,  # Both should match
                        'price': trade_price,
                        'quantity': trade_quantity
                    }
                )

            # If the resting order still has quantity left, re-insert it into the heap
            if best_opposite_order.quantity > 0:
                heapq.heappush(opposite_heap, best_opposite_order)

        # If there's still quantity left on the market order, we've exhausted the order book's best prices
        # or the buyer can't afford more. We do not re-add the remainder of a market order, as market orders
        # do not rest on the order book.

        # Return True if the order was partially or fully filled at least once
        return order_filled

    # TODO: make better after testing
    def remove_order(self, order_id: str) -> bool:
        order = self.order_map.pop(order_id, None)
        if order is None:
            return False
        order.orderLife = "CANCELLED"
        return True
    
    timescalled = 0

    def match_orders(self):
        while self.bids and self.asks:
            print(f"{self.symbol}: called {self.timescalled} and {len(self.bids)} items in bids heap")
            self.timescalled += 1
            highest_bid = heapq.heappop(self.bids)
            lowest_ask = heapq.heappop(self.asks)

            result, trade = self.attemptMatch(highest_bid, lowest_ask)

            if result == MatchResult.SUCCESS:
                highest_bid.orderLife = "FILLED"
                lowest_ask.orderLife = "FILLED"

            else:
                # Re-add if no trade
                heapq.heappush(self.bids, highest_bid)
                heapq.heappush(self.asks, lowest_ask)
                break


    def get_order_book(self) -> dict:
        """
        Return the current snapshot of non-removed orders, sorted appropriately.
        """
        # Filter out removed items. We do NOT pop them from the heap here,
        # but let's produce a sorted snapshot.
        valid_bids = [(o.price, o.quantity, o.timestamp, o.order_id)
                      for o in self.bids if not o.orderLife == "CANCELLED"]
        valid_asks = [(o.price, o.quantity, o.timestamp, o.order_id)
                      for o in self.asks if not o.orderLife == "CANCELLED"]

        # Sort for display
        valid_bids.sort(key=lambda x: (-x[0], x[2]))  # highest price first
        valid_asks.sort(key=lambda x: (x[0], x[2]))   # lowest price first

        return {
            'bids': valid_bids,
            'asks': valid_asks
        }

    def attemptMatch(self, highest_bid: Order, lowest_ask: Order) -> Tuple[
        MatchResult, Union[Tuple[Order, Order, float, float], str]]:
        # Matching logic remains as before, just without locks
        if highest_bid.order_type == 'limit' and lowest_ask.order_type == 'limit':
            if highest_bid.price < lowest_ask.price:
                return MatchResult.PRICE_MISMATCH_ERROR, "No matches available"
        if highest_bid.participant_id == lowest_ask.participant_id:
            return MatchResult.SELF_TRADE_ERROR, "Cannot trade with oneself"

        # Determine trade price
        if highest_bid.order_type == 'market' and lowest_ask.order_type == 'market':
            # Just pick lowest_ask price for now or fallback to highest_bid, some logic needed
            raise ValueError("there is a market order in the book")
        elif highest_bid.order_type == 'market':
            raise ValueError("there is a market order in the book")
        elif lowest_ask.order_type == 'market':
            raise ValueError("there is a market order in the book")
        else:
            trade_price = lowest_ask.price

        trade_quantity = min(highest_bid.quantity, lowest_ask.quantity)
        addBackBid = (highest_bid.quantity > lowest_ask.quantity)
        addBackAsk = (highest_bid.quantity < lowest_ask.quantity)

        total_cost = trade_quantity * trade_price
        buyerBalance = self.pm.get_participant_balance(participant_id=highest_bid.participant_id)

        if buyerBalance < total_cost:
            trade_quantity = int(buyerBalance // trade_price)
            if trade_quantity < lowest_ask.quantity:
                addBackAsk = True

        if trade_quantity <= 0:
            # Can't trade
            return MatchResult.INSUFFICIENT_BALANCE_ERROR, "Buyer has insufficient balance"

        # can do call to participant manager -> each participant, me thinks (then after get chatgpt to thread it)
        # don't need buyer object here

        self.pm.send_execution_report(
            buyer_participant_id=highest_bid.participant_id,
            seller_participant_id=lowest_ask.participant_id,
            trade_details={
                'buyer_order_id': highest_bid.order_id,
                'seller_order_id': lowest_ask.order_id,
                'symbol': highest_bid.symbol,
                'price': trade_price,
                'quantity': trade_quantity
            })

        if addBackAsk:
            lowest_ask.quantity -= trade_quantity
            heapq.heappush(self.asks, lowest_ask)
        if addBackBid:
            highest_bid.quantity -= trade_quantity
            heapq.heappush(self.bids, highest_bid)

        return MatchResult.SUCCESS, (highest_bid, lowest_ask, trade_price, trade_quantity)

    def get_highest_bid(self) -> float:
        while self.bids:
            top = self.bids[0]  # peek instead of pop
            if top.orderLife == "CANCELLED":
                heapq.heappop(self.bids)  # remove only if cancelled
            else:
                return top.price
        return 0.0

    def get_lowest_ask(self) -> float:
        while self.asks:
            top = self.asks[0]
            if top.orderLife == "CANCELLED":
                heapq.heappop(self.asks)
            else:
                return top.price
