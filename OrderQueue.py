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
        """
        Initializes the PerTickerOrderQueue with a dictionary of order books.
        :param order_books: A dictionary mapping ticker symbols to their OrderBook instances.
        """
        self.ticker_queues: Dict[str, deque] = {}
        self.match_engines: Dict[str, MatchEngine] = {}
        self.conditions: Dict[str, threading.Condition] = {}
        self.order_books = order_books  # Access to order books for each ticker
        self.lock = threading.Lock()


    def add_order_book(self, ticker: str, book: LimitOrderBook, pm):
        self.order_books[ticker] = book
        self.match_engines[ticker] = MatchEngine(book, pm)
        self.create_ticker_queue(ticker)

    def create_ticker_queue(self, ticker: str):
        """
        Creates a queue and condition for a new ticker, then starts a worker thread.
        """
        with self.lock:
            if ticker not in self.ticker_queues:
                self.ticker_queues[ticker] = deque()
                self.conditions[ticker] = threading.Condition()  # Create a condition for this ticker
                threading.Thread(
                    target=self._process_ticker_orders,
                    args=(ticker,),
                    daemon=True
                ).start()

    def put_order(self, order: Order):
        """
        Adds an order to the appropriate ticker queue.
        If the queue doesn't exist, an error is raised.
        """
        if order.symbol not in self.ticker_queues:
            raise ValueError(f"No queue exists for ticker: {order.symbol}")

        with self.conditions[order.symbol]:
            if order.price is None:
                self.ticker_queues[order.symbol].appendleft(order)
            else:
                order.price = round(order.price, 2)
                self.ticker_queues[order.symbol].append(order)

            self.conditions[order.symbol].notify()  # Notify the worker thread that an order is available

    def _process_ticker_orders(self, ticker: str):
        """
        Worker thread to continuously process orders for a specific ticker.
        """
        while True:
            with self.conditions[ticker]:
                while not self.ticker_queues[ticker]:
                    self.conditions[ticker].wait()  # Wait until an order is added to the queue

                order: Order = self.ticker_queues[ticker].popleft()

            # Process the order outside the lock
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

    # def get_order_for_ticker(self, ticker: str) -> Order:
    #     """
    #     Retrieves the next order for the specified ticker.
    #     """
    #     with self.conditions[ticker]:
    #         while not self.ticker_queues[ticker]:
    #             self.conditions[ticker].wait()
    #         return self.ticker_queues[ticker].popleft()


### USAGE::

# if __name__ == "__main__":
#     # Create participant manager and order books for tickers
#     pm = ParticipantManager()
#     order_books = {
#         "AAPL": OrderBook("AAPL", pm),
#         "GOOGL": OrderBook("GOOGL", pm),
#         "AMZN": OrderBook("AMZN", pm),
#     }

#     # Create the PerTickerOrderQueue manager
#     order_queue_manager = PerTickerOrderQueue(order_books)

#     # Create queues for each ticker
#     order_queue_manager.create_ticker_queue("AAPL")
#     order_queue_manager.create_ticker_queue("GOOGL")
#     order_queue_manager.create_ticker_queue("AMZN")
