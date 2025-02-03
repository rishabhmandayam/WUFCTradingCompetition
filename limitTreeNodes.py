from OrderList import OrderList

class LimitLevel:
    """AVL BST node with cached height."""

    __slots__ = [
        'price', 'size', 'parent', 'left_child', 'right_child', 'orders',
        '_height'  # <-- store cached height here
    ]

    def __init__(self, order):
        # Data Values
        self.price = order.price
        self.size = order.size

        # BST Attributes
        self.parent = None
        self.left_child = None
        self.right_child = None
        
        # Cached height (start as leaf = 1)
        self._height = 1

        # Doubly-linked-list attributes
        self.orders = OrderList(self)
        self.append(order)

    @property
    def is_root(self):
        return isinstance(self.parent, LimitLevelTree)

    @property
    def volume(self):
        return self.price * self.size

    @property
    def balance_factor(self):
        """
        For AVL, balance_factor = height(right_subtree) - height(left_subtree).
        """
        right_height = self.right_child._height if self.right_child else 0
        left_height = self.left_child._height if self.left_child else 0
        return right_height - left_height

    @property
    def grandpa(self):
        if self.parent and not isinstance(self.parent, LimitLevelTree):
            return self.parent.parent
        return None

    @property
    def height(self):
        """
        O(1) property that returns the cached height.
        """
        return self._height

    def _update_height(self):
        """
        Recompute height based on children's heights:
            self._height = max(height(left), height(right)) + 1
        """
        left_height = self.left_child._height if self.left_child else 0
        right_height = self.right_child._height if self.right_child else 0
        self._height = max(left_height, right_height) + 1

    @property
    def min(self):
        node = self
        while node.left_child:
            node = node.left_child
        return node

    def append(self, order):
        self.orders.append(order)

    def _replace_node_in_parent(self, new_value=None):
        if self.is_root:
            # self.parent is a LimitLevelTree in this case
            self.parent.right_child = new_value
            if new_value:
                new_value.parent = self.parent
        else:
            # The usual case for non-root nodes
            if self == self.parent.left_child:
                self.parent.left_child = new_value
            else:
                self.parent.right_child = new_value

            # After replacing, parent might need an update in height
            self.parent._update_height()

            if new_value:
                new_value.parent = self.parent


    def remove(self):
        """
        Removes this node from the BST, substituting with a child if any.
        Also calls balance on the grandpa if needed.
        """
        if self.left_child and self.right_child:
            # Two children: swap with successor, then remove successor
            successor = self.right_child.min
            self.price, self.size = successor.price, successor.size
            successor.remove()
            self.balance_grandpa()
        elif self.left_child:
            self._replace_node_in_parent(self.left_child)
        elif self.right_child:
            self._replace_node_in_parent(self.right_child)
        else:
            self._replace_node_in_parent(None)

    def balance_grandpa(self):
        if self.grandpa and isinstance(self.grandpa, LimitLevel):
            self.grandpa.balance()

    def balance(self):
        """
        Rebalance this node if AVL property is violated.
        Then recurse upward if needed.
        """
        # Update our own height first (important for correct balance_factor)
        self._update_height()

        if self.is_root:
            return  # The tree "root" is actually a LimitLevelTree, so skip

        # Check balance factor to decide if rotation is needed
        if self.balance_factor > 1:
            # Right-heavy
            if self.right_child.balance_factor < 0:
                self._rl_case()
            else:
                self._rr_case()
        elif self.balance_factor < -1:
            # Left-heavy
            if self.left_child.balance_factor < 0:
                self._ll_case()
            else:
                self._lr_case()

        # After potential rotation(s), update height again
        self._update_height()

        # Continue balancing up the tree if needed
        if self.parent and not self.parent.is_root:
            self.parent.balance()

    def _ll_case(self):
        """
        Right rotation around 'self'.
        """
        child = self.left_child
        # Connect child to self.parent
        if self.is_root:
            self.parent.right_child = child
        elif self.parent.left_child == self:
            self.parent.left_child = child
        else:
            self.parent.right_child = child

        child.parent = self.parent
        # Rotate
        self.left_child = child.right_child
        if self.left_child:
            self.left_child.parent = self
        child.right_child = self
        self.parent = child

        # Update heights bottom-up
        self._update_height()
        child._update_height()

    def _rr_case(self):
        """
        Left rotation around 'self'.
        """
        child = self.right_child
        # Connect child to self.parent
        if self.is_root:
            self.parent.right_child = child
        elif self.parent.left_child == self:
            self.parent.left_child = child
        else:
            self.parent.right_child = child

        child.parent = self.parent
        # Rotate
        self.right_child = child.left_child
        if self.right_child:
            self.right_child.parent = self
        child.left_child = self
        self.parent = child

        # Update heights bottom-up
        self._update_height()
        child._update_height()

    def _lr_case(self):
        """
        Left->Right rotation: rotate left child right, then self left.
        """
        child, grand_child = self.left_child, self.left_child.right_child
        # "Rotate" child -> grand_child
        child.parent, grand_child.parent = grand_child, self
        child.right_child = grand_child.left_child
        if child.right_child:
            child.right_child.parent = child
        self.left_child, grand_child.left_child = grand_child, child
        # Now do an LL rotation
        self._ll_case()

    def _rl_case(self):
        """
        Right->Left rotation: rotate right child left, then self right.
        """
        child, grand_child = self.right_child, self.right_child.left_child
        # "Rotate" child -> grand_child
        child.parent, grand_child.parent = grand_child, self
        child.left_child = grand_child.right_child
        if child.left_child:
            child.left_child.parent = child
        self.right_child, grand_child.right_child = grand_child, child
        # Now do an RR rotation
        self._rr_case()

    def __str__(self):
        if not self.is_root:
            s = f'Node Value: {self.price}\n'
            s += f'Node left_child value: {self.left_child.price if self.left_child else "None"}\n'
            s += f'Node right_child value: {self.right_child.price if self.right_child else "None"}\n\n'
        else:
            s = ''

        left_side_print = self.left_child.__str__() if self.left_child else ''
        right_side_print = self.right_child.__str__() if self.right_child else ''
        return s + left_side_print + right_side_print

    def __len__(self):
        return len(self.orders)


class LimitLevelTree:
    __slots__ = ['right_child']

    def __init__(self):
        self.right_child = None

    def insert(self, limit_level):
        if self.right_child is None:
            self.right_child = limit_level
            self.right_child.parent = self
            return

        current_node = self.right_child
        while True:
            if limit_level.price > current_node.price:
                if current_node.right_child is None:
                    current_node.right_child = limit_level
                    limit_level.parent = current_node
                    # After attaching, rebalance upward
                    limit_level.balance_grandpa()
                    break
                else:
                    current_node = current_node.right_child
            elif limit_level.price < current_node.price:
                if current_node.left_child is None:
                    current_node.left_child = limit_level
                    limit_level.parent = current_node
                    # After attaching, rebalance upward
                    limit_level.balance_grandpa()
                    break
                else:
                    current_node = current_node.left_child
            else:
                raise ValueError(f"LimitLevel with price {limit_level.price} already exists. also this is")

    def find(self, price):
        current_node = self.right_child
        while current_node:
            if current_node.price == price:
                return current_node
            elif price < current_node.price:
                current_node = current_node.left_child
            else:
                current_node = current_node.right_child
        return None
