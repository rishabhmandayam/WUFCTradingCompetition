# exchange/participant.py

import threading
import time
from typing import Dict, Any, Optional

# Import the Order class INSIDE participant; not exposed to competitor
from orderForTree import Order

class Participant:
    def __init__(self, participant_id: str, balance: float = 100000.0,
                 order_book_manager=None, order_queue_manager=None):

        self.participant_id = participant_id
        self.__balance = balance
        self.__portfolio: Dict[str, int] = {}

        self.__order_book_manager = order_book_manager
        self.__order_queue_manager = order_queue_manager

        self.__round_ended_event: Optional[threading.Event] = None
        self.strategy_interval = 0.1
        self.__thread = None


    def create_limit_order(self, price: float, size: int, side: str, symbol: str) -> Optional[str]:

        try:
            order = Order.create_limit_order(
                price=price,
                size=size,
                side=side,
                participant_id=self.participant_id,
                symbol=symbol
            )
        except ValueError as e:

            return None

        success = self._place_order_in_queue(order)
        return order.order_id if success else None

    def create_market_order(self, size: int, side: str, symbol: str) -> Optional[str]:

        try:
            order = Order.create_market_order(
                size=size,
                side=side,
                participant_id=self.participant_id,
                symbol=symbol
            )
        except ValueError as e:
            return None

        success = self._place_order_in_queue(order)
        return order.order_id if success else None

    def remove_order(self, order_id: str, symbol: str) -> bool:

        cancel_order = Order.create_cancel_order(
            order_id=order_id,
            participant_id=self.participant_id,
            symbol=symbol
        )
        return self._place_order_in_queue(cancel_order)

    def _place_order_in_queue(self, order: Order) -> bool:

        if order.is_bid and order.order_type == 'limit' and order.price is not None:
            total_cost = order.price * order.size
            if self.__balance < total_cost:
                return False

        if not self.__order_queue_manager:
            return False

        try:
            self.__order_queue_manager.put_order(order)
            return True
        except ValueError as e:
            return False

    @property
    def get_balance(self) -> float:
        return self.__balance

    @property
    def get_portfolio(self) -> Dict[str, int]:
        return self.__portfolio

    def get_order_book_snapshot(self, symbol: str) -> Dict[str, Any]:
        if not self.__order_book_manager:
            raise ValueError("Order book manager not initialized.")
        return self.__order_book_manager.get_order_book_snapshot(symbol)

    def get_orderbook_price(self, symbol: str, isBid: bool):
        if not self.__order_book_manager:
            raise ValueError("Order book manager not initialized.")
        return self.__order_book_manager.get_best_price(symbol=symbol, isBid=isBid)




    def receive_execution_report(self, report: Dict[str, Any]):

        
        side = report.get('side')
        price = report.get('price')
        qty = report.get('quantity')
        symbol = report.get('symbol', 'UNKNOWN')
    
        if side == 'buy':
            self.__balance -= price * qty
            self.__portfolio[symbol] = self.__portfolio.get(symbol, 0) + qty
        elif side == 'sell':
            self.__balance += price * qty
            self.__portfolio[symbol] = self.__portfolio.get(symbol, 0) - qty

    def strategy(self):

        pass

    def start(self, round_ended_event: threading.Event, strategy_interval: float = 0.1):

        self.__round_ended_event = round_ended_event
        self.strategy_interval = strategy_interval

        if self.__thread is None:
            self.__thread = threading.Thread(target=self._run_loop, daemon=True)
            self.__thread.start()

    def _run_loop(self):

        while not self.__round_ended_event.is_set():
            self.strategy()
            time.sleep(self.strategy_interval)
