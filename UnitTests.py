import threading
import unittest
from MatchEngine import MatchEngine
from limitOrderBook import LimitOrderBook
from orderForTree import Order
from ParticipantManager import ParticipantManager
from OrderBookManager import OrderBookManager
from Participant import Participant
import time

class TestConcurrentLimitOrders(unittest.TestCase):
    def setUp(self):
        """Set up the test environment."""
        self.symbol = "AAPL"
        pm = ParticipantManager()
        order_book_manager = OrderBookManager(pm)
        self.order_queue_manager = order_book_manager.orderQueue
        order_book_manager.add_order_book(self.symbol)

        self.order_book = order_book_manager.order_books[self.symbol]
        self.match_engine = self.order_queue_manager.match_engines[self.symbol]

        # Add participants
        p1 = Participant("P1")
        p2 = Participant("P2")
        p3 = Participant("P3")  # Needed for tests with more than 2 participants
        pm.add_participant(p1)
        pm.add_participant(p2)
        pm.add_participant(p3)

    def test_add_3_bids_same_price_concurrently_and_remove_them(self):
        """
        Test adding 3 buy (bid) orders at the same price at the same time,
        then removing them.
        """
        def add_order(order):
            self.order_queue_manager.put_order(order)

        # Create three concurrent limit orders (all bids) at the same price
        order1 = Order.create_limit_order(price=145.00, size=5, side="buy", participant_id="P1", symbol=self.symbol)
        order2 = Order.create_limit_order(price=145.00, size=10, side="buy", participant_id="P2", symbol=self.symbol)
        order3 = Order.create_limit_order(price=145.00, size=15, side="buy", participant_id="P3", symbol=self.symbol)

        t1 = threading.Thread(target=add_order, args=(order1,))
        t2 = threading.Thread(target=add_order, args=(order2,))
        t3 = threading.Thread(target=add_order, args=(order3,))

        t1.start(); t2.start(); t3.start()
        t1.join();  t2.join();  t3.join()

        # Let the orders get processed
        time.sleep(0.000015)

        # Check the price level
        price_level = self.order_book._price_levels.get((145.00, True))
        self.assertIsNotNone(price_level, "Expected price level for 145.00 was not found.")
        self.assertEqual(price_level.orders.count, 3, "Should have exactly 3 orders at this price.")

        # --- Now remove them concurrently ---
        def remove_order(order):
            self.order_book.remove(order)

        # Alternatively, if your architecture supports "cancel" orders:
        # def cancel_order(order):
        #     cancel = Order.create_cancel_order(order_id=order.order_id, ...)
        #     self.order_queue_manager.put_order(cancel)

        thread_remove_1 = threading.Thread(target=remove_order, args=(order1,))
        thread_remove_2 = threading.Thread(target=remove_order, args=(order2,))
        thread_remove_3 = threading.Thread(target=remove_order, args=(order3,))

        thread_remove_1.start()
        thread_remove_2.start()
        thread_remove_3.start()

        thread_remove_1.join()
        thread_remove_2.join()
        thread_remove_3.join()

        time.sleep(0.000015)

        # After removal, the price level should either be gone or have 0 orders
        price_level_after = self.order_book._price_levels.get((145.00, True), None)
        if price_level_after is not None:
            self.assertEqual(price_level_after.orders.count, 0, "Price level still has orders after removal.")
        else:
            # Also acceptable if the order book discards empty levels automatically
            pass

    def test_concurrent_2_asks_1_bid_same_time_match(self):
        """
        Test adding 2 ask orders and 1 bid order concurrently, ensuring
        the matching occurs if the bid crosses the ask.
        """
        def add_order(order):
            self.order_queue_manager.put_order(order)

        # Create two asks and one bid at crossing prices so a match will occur
        ask1 = Order.create_limit_order(price=140.00, size=10, side="sell", participant_id="P1", symbol=self.symbol)
        ask2 = Order.create_limit_order(price=140.00, size=5, side="sell", participant_id="P2", symbol=self.symbol)
        bid1 = Order.create_limit_order(price=145.00, size=8, side="buy", participant_id="P3", symbol=self.symbol)

        t1 = threading.Thread(target=add_order, args=(ask1,))
        t2 = threading.Thread(target=add_order, args=(ask2,))
        t3 = threading.Thread(target=add_order, args=(bid1,))

        t1.start(); t2.start(); t3.start()
        t1.join();  t2.join();  t3.join()

        time.sleep(0.000015)

        # If the bid (145) is greater than the ask (140),
        # the match engine should fill at 140, partially or fully.
        # Check final sizes or check if the order book is empty at 140 or 145.

        # For instance, check how many shares remain on each:
        self.assertTrue(ask1.size < 10 or ask2.size < 5 or bid1.size < 8,
                        "Expected a match to have occurred, but no sizes were reduced.")

        # You can further check the order book levels:
        asks_at_140 = self.order_book._price_levels.get(140.00, None)
        if asks_at_140:
            # Possibly partially filled or empty
            self.assertIn(asks_at_140.orders.count, [1, 2, 0],
                "Number of orders at 140.00 is unexpected after matching.")
        # Possibly check the price level at 145 for residual bid

    def test_concurrent_2_asks_2_bids_same_time(self):
        """
        Test adding 2 asks and 2 bids at the same time.
        If the bid >= ask, we should see matches.
        """
        def add_order(order):
            self.order_queue_manager.put_order(order)

        ask1 = Order.create_limit_order(price=100.00, size=10, side="sell", participant_id="P1", symbol=self.symbol)
        ask2 = Order.create_limit_order(price=105.00, size=10, side="sell", participant_id="P2", symbol=self.symbol)
        bid1 = Order.create_limit_order(price=110.00, size=5, side="buy", participant_id="P3", symbol=self.symbol)
        bid2 = Order.create_limit_order(price=107.00, size=10, side="buy", participant_id="P2", symbol=self.symbol)

        t1 = threading.Thread(target=add_order, args=(ask1,))
        t2 = threading.Thread(target=add_order, args=(ask2,))
        t3 = threading.Thread(target=add_order, args=(bid1,))
        t4 = threading.Thread(target=add_order, args=(bid2,))

        t1.start(); t2.start(); t3.start(); t4.start()
        t1.join();  t2.join();  t3.join();  t4.join()

        time.sleep(0.0015)

        # Because bid1 = 110, it should definitely match with ask1 at 100
        # Possibly also with ask2 at 105. Then bid2 at 102 might match ask1 or ask2 
        # depending on how the first trades consumed them.

        # We can test if all asks are fully filled or partially:
        asks_at_100 = self.order_book._price_levels.get(100.00, None)
        asks_at_105 = self.order_book._price_levels.get((105.00, False), None)
        bids_at_107 = self.order_book._price_levels.get((107.00, True), None)
        self.assertEqual(bids_at_107,None)
        self.assertEqual(asks_at_105.size,5)
        
        # There's no single "right" answer without a fully-specified matching policy,
        # so adapt your assertions based on how your engine performs partial fills.

        # Example check: at least one ask must have been filled partially or fully
        self.assertTrue(ask1.size < 10 or ask2.size < 10,
                        "Expected at least one ask to have been matched but no size reduced.")


    def test_concurrent_limit_orders(self):
        """Test adding two limit orders at the same price concurrently."""
        def add_order(order):
            self.order_queue_manager.put_order(order)

        # Create two limit orders at the same price
        order1 = Order.create_limit_order(price=150.00, size=10, side="buy", participant_id="P1", symbol=self.symbol)
        order2 = Order.create_limit_order(price=150.00, size=20, side="buy", participant_id="P2", symbol=self.symbol)

        # Add orders concurrently
        thread1 = threading.Thread(target=add_order, args=(order1,))
        thread2 = threading.Thread(target=add_order, args=(order2,))

        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()
        
        time.sleep(0.000015)
        # Verify that the price level contains two items
        price_level = self.order_book._price_levels.get((150.00, True))  # Access the price level directly
        self.assertIsNotNone(price_level, "Price level does not exist")
        
        self.assertEqual(len(price_level.orders), 2, "Price level didn't have just 1 orderlist")
        if (price_level.orders.head.size == 10):
            self.assertEqual(price_level.orders.head.size, 10, "First order size does not match")
            self.assertEqual(price_level.orders.head.next_item.size, 20, "Second order size does not match")
        else:
            self.assertEqual(price_level.orders.head.size, 20, "First order size does not match")
            self.assertEqual(price_level.orders.tail.size, 10, "Second order size does not match")
            


if __name__ == "__main__":
    unittest.main()
