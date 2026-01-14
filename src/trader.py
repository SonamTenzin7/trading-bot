import pandas as pd
from datetime import datetime

class Trader:
    def __init__(self, initial_capital=10000):
        self.capital = initial_capital
        self.portfolio = {"USDT": initial_capital, "BTC": 0, "ETH": 0}
        self.trades = []
        self.position = None # Current position: None, 'LONG'
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
        
        # Risk Params
        self.risk_per_trade = 0.10 # 10% of portfolio
        self.sl_pct = 0.02 # 2%
        self.tp_pct = 0.05 # 5%

    def set_risk_params(self, size_pct, sl_pct, tp_pct):
        self.risk_per_trade = size_pct
        self.sl_pct = sl_pct
        self.tp_pct = tp_pct

    def execute_trade(self, signal, symbol, current_price, timestamp):
        """
        Executes paper trade based on signal and risk management.
        """
        reason = ""
        action = None
        
        # Check active position exits
        if self.position == 'LONG':
            # Check Stop Loss
            if current_price <= self.stop_loss:
                action = 'SELL'
                reason = 'Stop Loss Hit'
            # Check Take Profit
            elif current_price >= self.take_profit:
                action = 'SELL'
                reason = 'Take Profit Hit'
            # Check Signal Reversal
            elif signal == 'SELL':
                action = 'SELL'
                reason = 'Signal Reversal'
            
            if action == 'SELL':
                # Sell implementation
                coin = symbol.replace("USDT", "")
                amount = self.portfolio.get(coin, 0)
                if amount > 0:
                    revenue = amount * current_price
                    self.portfolio["USDT"] += revenue
                    self.portfolio[coin] = 0
                    self.position = None
                    profit = (current_price - self.entry_price) / self.entry_price
                    pnl_dollars = revenue - (self.entry_price * amount)
                    trade_info = {
                        'time': timestamp,
                        'symbol': symbol,
                        'action': 'SELL',
                        'price': current_price,
                        'amount': amount,
                        'reason': reason,
                        'profit_pct': profit,
                        'pnl': pnl_dollars
                    }
                    self.trades.append(trade_info)
                    print(f"SOLD {coin} at {current_price} ({reason}) PnL: {profit*100:.2f}%")
                    return trade_info

        elif self.position is None:
            if signal == 'BUY':
                # Buy implementation
                cost = self.portfolio["USDT"] * self.risk_per_trade
                if cost > 10: # Min trade size check
                    amount = cost / current_price
                    self.portfolio["USDT"] -= cost
                    coin = symbol.replace("USDT", "")
                    self.portfolio[coin] = self.portfolio.get(coin, 0) + amount
                    
                    self.position = 'LONG'
                    self.entry_price = current_price
                    self.stop_loss = current_price * (1 - self.sl_pct)
                    self.take_profit = current_price * (1 + self.tp_pct)
                    
                    self.trades.append({
                        'time': timestamp,
                        'symbol': symbol,
                        'action': 'BUY',
                        'price': current_price,
                        'amount': amount,
                        'reason': 'Signal Buy',
                        'profit_pct': 0
                    })
                    print(f"BOUGHT {coin} at {current_price}. SL: {self.stop_loss}, TP: {self.take_profit}")
        return None

    def get_portfolio_value(self, current_prices):
        val = self.portfolio["USDT"]
        for coin, amount in self.portfolio.items():
            if coin == "USDT": continue
            # find price for coin (e.g. BTC for BTCUSDT)
            symbol = f"{coin}USDT"
            price = current_prices.get(symbol, 0)
            val += amount * price
        return val
