from pdb import pm
import threading
import time
from collections import deque
from typing import Dict
from orderForTree import Order
from limitOrderBook import LimitOrderBook  
from MatchEngine import MatchEngine


class PerTickerOrderQueue:
    def __init__(self, order_books: Dict[str, LimitOrderBook]):

        self.ticker_queues: Dict[str, deque] = {}
        self.match_engines: Dict[str, MatchEngine] = {}
        self.conditions: Dict[str, threading.Condition] = {}
        self.order_books = order_books
        self.lock = threading.Lock()


    def add_order_book(self, ticker: str, book: LimitOrderBook, pm):
        self.order_books[ticker] = book
        self.match_engines[ticker] = MatchEngine(book, pm)
        self.create_ticker_queue(ticker)

    def create_ticker_queue(self, ticker: str):

        with self.lock:
            if ticker not in self.ticker_queues:
                self.ticker_queues[ticker] = deque()
                self.conditions[ticker] = threading.Condition()
                threading.Thread(
                    target=self._process_ticker_orders,
                    args=(ticker,),
                    daemon=True
                ).start()

    def put_order(self, order: Order):

        if order.symbol not in self.ticker_queues:
            raise ValueError(f"No queue exists for ticker: {order.symbol}")

        with self.conditions[order.symbol]:
            if order.price is None:
                self.ticker_queues[order.symbol].appendleft(order)
            else:
                order.price = round(order.price, 2)
                self.ticker_queues[order.symbol].append(order)

            self.conditions[order.symbol].notify()

    def _process_ticker_orders(self, ticker: str):

        while True:
            with self.conditions[ticker]:
                while not self.ticker_queues[ticker]:
                    self.conditions[ticker].wait()

                order: Order = self.ticker_queues[ticker].popleft()

                if ticker in self.order_books:
                    match_engine = self.match_engines[ticker]
                    if order.order_type == "limit":
                        match_engine.acceptLimitOrder(order)
                    elif order.order_type == "market":
                        match_engine.acceptMarketOrder(order)
                    elif order.order_type == "cancel":
                        match_engine.acceptCancelOrder(order)
                    else:
                        raise ValueError("order_type is invalid")

