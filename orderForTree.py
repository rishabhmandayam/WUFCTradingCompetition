import time
import uuid
from typing import Optional
from dataclasses import dataclass

@dataclass
class Order:
    """Doubly-Linked List Order item.

    Keeps a reference to root, as well as previous and next order in line.

    It also performs any and all updates to the root's tail, head and count
    references, as well as updating the related LimitLevel's size, whenever
    a method is called on this instance.

    Offers append() and pop() methods. Prepending isn't implemented.

    """

    order_id: str
    timestamp: float
    price: Optional[float]  # None for market orders
    size: int
    is_bid: bool  # true for 'buy' and false for 'sell'
    order_type: str  # 'market' or 'limit' or 'cancel'
    participant_id: str
    symbol: str  # Ticker symbol of the security

    

    def __post_init__(self):
        #DLL attributes
        self.next_item = None
        self.previous_item = None
        self.root = None

    @property
    def parent_limit(self):
        return self.root.parent_limit

    def append(self, order):
        """Append an order.

        :param order: Order() instance
        :return:
        """
        if self.next_item is None:
            self.next_item = order
            self.next_item.previous_item = self
            self.next_item.root = self.root
            

            # Update Root Statistics in OrderList root obj
            self.root.count += 1
            self.root.tail = order

            self.parent_limit.size += order.size
            

        else:
            #this shouldn't happen.
            self.root.append(order)
            #self.root.tail.append(order)
            #self.next_item.append(order)

    def pop_from_list(self):
        """Pops this item from the DoublyLinkedList it belongs to.

        :return: Order() instance values as tuple
        """
        if self.previous_item is None:
            # We're head
            self.root.head = self.next_item
            if self.next_item:
                self.next_item.previous_item = None

        elif self.next_item is None:
            # We're tail
            self.root.tail = self.previous_item
            if self.previous_item:
                self.previous_item.next_item = None

        # Update the Limit Level and root
        self.root.count -= 1
        self.parent_limit.size -= self.size

        return self.__repr__()
    
    @staticmethod
    def create_limit_order(price: float, size: int, side: str, participant_id: str, symbol: str) -> 'Order':
       
        if price <= 0:
            raise ValueError("Limit order price must be positive.")
        if size <= 0:
            raise ValueError("Order size must be positive.")
        if (side == 'buy'):
            is_bid = True
        elif (side == 'sell'):
            is_bid = False
        else:
            raise ValueError("Limit Order has to be of side 'buy' or 'sell'")
        
        return Order(
            order_id=str(uuid.uuid4()),
            timestamp=time.time(),
            price=price,
            size=size,
            is_bid=is_bid,
            order_type='limit',
            participant_id=participant_id,
            symbol=symbol
        )

    @staticmethod
    def create_market_order(size: int, side: str, participant_id: str, symbol: str) -> 'Order':
        """
        Factory method to create a market order.
        """
        if (side == 'buy'):
            is_bid = True
        elif (side == 'sell'):
            is_bid = False
        else:
            raise ValueError("Market Order has to be of side 'buy' or 'sell'")

        return Order(
            order_id=str(uuid.uuid4()),
            timestamp=time.time(),
            price=None,  # Market orders do not have a price
            size=size,
            is_bid=is_bid,
            order_type='market',
            participant_id=participant_id,
            symbol=symbol
        )
    
    @staticmethod
    def create_cancel_order(order_id: str, participant_id: str, symbol: str):
        
        return Order(
            order_id=order_id,
            timestamp=time.time(),
            price=None,
            size=0,
            is_bid=True,
            order_type='cancel',
            participant_id=participant_id,
            symbol=symbol,
        )

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return str((self.order_id, self.is_bid, self.price, self.size, self.timestamp))