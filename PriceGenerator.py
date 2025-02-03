# exchange/price_generator.py

import threading
import time
import numpy as np
from typing import Dict, Any, Callable, Optional

class PriceGenerator:
    def __init__(self, seed: Optional[int] = None):

        self.securities: Dict[str, Dict[str, Any]] = {}
        self.current_prices: Dict[str, float] = {}
        self.lock = threading.Lock()
        self.seed = seed
        self.random_state = np.random.RandomState(seed)
        self.running = False
        self.thread = threading.Thread(target=self.run, daemon=True)

    def add_security(self, symbol: str, initial_price: float, drift: float, volatility: float, time_step: float = 1.0):

        with self.lock:
            self.securities[symbol] = {
                'price': initial_price,
                'drift': drift,
                'volatility': volatility,
                'time_step': time_step
            }
            self.current_prices[symbol] = initial_price

    def start(self):

        self.running = True
        self.thread.start()

    def stop(self):

        self.running = False
        self.thread.join()

    def run(self):

        while self.running:
            start_time = time.time()
            with self.lock:
                for symbol, params in self.securities.items():
                    price = self.current_prices[symbol]
                    drift = params['drift']
                    volatility = params['volatility']
                    dt = params['time_step']

                    Z = self.random_state.standard_normal()
                    price_change_factor = np.exp((drift - 0.5 * volatility ** 2) * dt +
                                                 volatility * np.sqrt(dt) * Z)
                    new_price = price * price_change_factor
                    self.current_prices[symbol] = new_price
            dt = 1.0
            elapsed = time.time() - start_time
            sleep_time = max(0, dt - elapsed)
            time.sleep(sleep_time)

    def get_current_price(self, symbol: str) -> Optional[float]:

        with self.lock:
            return self.current_prices.get(symbol, None)

    def get_all_prices(self) -> Dict[str, float]:

        with self.lock:
            return self.current_prices.copy()

    def set_seed(self, seed: int):

        with self.lock:
            self.seed = seed
            self.random_state = np.random.RandomState(seed)

    def update_security_parameters(self, symbol: str, drift: Optional[float] = None, volatility: Optional[float] = None,
                                   time_step: Optional[float] = None):

        with self.lock:
            if symbol in self.securities:
                if drift is not None:
                    self.securities[symbol]['drift'] = drift
                if volatility is not None:
                    self.securities[symbol]['volatility'] = volatility
                if time_step is not None:
                    self.securities[symbol]['time_step'] = time_step


