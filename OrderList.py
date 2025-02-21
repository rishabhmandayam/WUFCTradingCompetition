import threading

class OrderList:
    __slots__ = ['head', 'tail', 'parent_limit', 'count', '_lock']

    def __init__(self, parent_limit):
        self.head = None
        self.tail = None
        self.count = 0
        self.parent_limit = parent_limit
        self._lock = threading.Lock()  # Added lock for thread safety

    def __len__(self):
        with self._lock:
            return self.count

    def append(self, order):
        with self._lock:
            # Set the order's root pointer to this OrderList.
            order.root = self

            # If the list is empty, initialize head and tail with the new order.
            if self.head is None:
                self.head = order
                self.tail = order
            else:
                # Otherwise, link the new order directly to the current tail.
                # Assumes that the order object has an attribute 'next_item'
                self.tail.next_item = order
                # (Optional) If you maintain a doubly-linked list, set the backward pointer:
                order.previous_item = self.tail
                # Now update the tail to be the new order.
                self.tail = order
                self.parent_limit.size += order.size
            self.count += 1

    def remove(self, order):
        with self._lock:
            if order is self.head:
                self.head = order.next_item
            if order is self.tail:
                self.tail = order.previous_item
            if order.previous_item:
                order.previous_item.next_item = order.next_item
            if order.next_item:
                order.next_item.previous_item = order.previous_item
            self.count -= 1
            self.parent_limit.size -= order.size

