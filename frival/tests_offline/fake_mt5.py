# -*- coding: utf-8 -*-
"""Fake MetaTrader5 module for the offline desk test harness (P0-01).

This is NOT the real MetaTrader5 package. The harness installs an instance of
``FakeMT5`` into ``sys.modules["MetaTrader5"]`` before importing the desk
modules under test, so the desk never touches a terminal, a live account, or
real market data.

It records every call (name + kwargs) in ``self.calls`` so a test can assert
what the desk asked the broker to do, and it lets a test program the responses
(positions, orders, ticks, symbol specs, ``None`` returns, exceptions).
"""
from __future__ import annotations


class Obj:
    """A trivial attribute bag, standing in for MT5's named-tuple results."""

    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __repr__(self):
        inner = ", ".join(f"{k}={v!r}" for k, v in sorted(self.__dict__.items()))
        return f"Obj({inner})"


def symbol_info(symbol="XAUUSD", digits=2, point=0.01, contract=100.0,
                tick_size=0.01, tick_value=1.0, vol_min=0.01, vol_step=0.01,
                vol_max=100.0):
    return Obj(name=symbol, digits=digits, point=point,
               trade_contract_size=contract, trade_tick_size=tick_size,
               trade_tick_value=tick_value, volume_min=vol_min,
               volume_step=vol_step, volume_max=vol_max)


def tick(symbol="XAUUSD", bid=2000.0, ask=2000.2, t=0):
    return Obj(symbol=symbol, bid=bid, ask=ask, time=t)


def position(symbol="XAUUSD", ticket=1, ptype=0, volume=0.1, price_open=2000.0,
             price_current=2000.0, sl=1990.0, tp=2020.0, profit=0.0, swap=0.0,
             comment="FRIVAL_T001", magic=20261001, time=0):
    return Obj(symbol=symbol, ticket=ticket, type=ptype, volume=volume,
               price_open=price_open, price_current=price_current, sl=sl, tp=tp,
               profit=profit, swap=swap, comment=comment, magic=magic, time=time)


def order(symbol="XAUUSD", ticket=11, otype=2, volume_current=0.1,
          price_open=2000.0, sl=1990.0, tp=2020.0, comment="FRIVAL_T001",
          magic=20261001):
    return Obj(symbol=symbol, ticket=ticket, type=otype,
               volume_current=volume_current, price_open=price_open, sl=sl,
               tp=tp, comment=comment, magic=magic)


class FakeMT5:
    # ── constants the desk reads ────────────────────────────────────────────
    TIMEFRAME_M1 = 1
    TIMEFRAME_M5 = 5
    TIMEFRAME_M15 = 15
    TIMEFRAME_M30 = 30
    TIMEFRAME_H1 = 16385
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TYPE_BUY_LIMIT = 2
    ORDER_TYPE_SELL_LIMIT = 3
    ORDER_TYPE_BUY_STOP = 4
    ORDER_TYPE_SELL_STOP = 5
    TRADE_ACTION_DEAL = 1
    TRADE_ACTION_PENDING = 5
    TRADE_ACTION_SLTP = 6
    TRADE_RETCODE_DONE = 10009
    TRADE_RETCODE_PLACED = 10008
    TRADE_RETCODE_DONE_PARTIAL = 10010
    TRADE_RETCODE_INVALID = 10013
    ORDER_TIME_GTC = 0
    DEAL_ENTRY_IN = 0
    DEAL_ENTRY_OUT = 1

    def __init__(self, sentinel_path="__NO_PATH__"):
        self.sentinel_path = sentinel_path
        self.calls = []
        self.initialized = False
        self.account = Obj(login=81486396, server="FPMarketsSC-Live",
                           equity=1000.0, balance=1000.0, margin=0.0,
                           margin_level=0.0, leverage=500, currency="USD")
        self.positions = []          # list of position() Obj
        self.orders = []             # list of order() Obj
        self.symbols = {}            # symbol -> symbol_info Obj
        self.ticks = {}              # symbol -> tick Obj
        self.init_returns = True
        self.positions_returns_none = False
        self.orders_returns_none = False
        self.rates = []              # rows for copy_rates_from_pos

    # ── recording ───────────────────────────────────────────────────────────
    def _rec(self, name, **kw):
        self.calls.append((name, kw))

    def called(self, name):
        return [kw for (n, kw) in self.calls if n == name]

    # ── MetaTrader5 surface used by the desk ────────────────────────────────
    def initialize(self, path=None, **kw):
        self._rec("initialize", path=path)
        self.initialized = self.init_returns
        return self.init_returns

    def last_error(self):
        self._rec("last_error")
        return (0, "fake-ok")

    def shutdown(self):
        self._rec("shutdown")

    def account_info(self):
        self._rec("account_info")
        return self.account

    def symbol_info(self, symbol):
        self._rec("symbol_info", symbol=symbol)
        return self.symbols.get(symbol)

    def symbol_info_tick(self, symbol):
        self._rec("symbol_info_tick", symbol=symbol)
        return self.ticks.get(symbol)

    def positions_get(self, symbol=None, **kw):
        self._rec("positions_get", symbol=symbol)
        if self.positions_returns_none:
            return None
        if symbol is None:
            return list(self.positions)
        return [p for p in self.positions if p.symbol == symbol]

    def orders_get(self, symbol=None, **kw):
        self._rec("orders_get", symbol=symbol)
        if self.orders_returns_none:
            return None
        if symbol is None:
            return list(self.orders)
        return [o for o in self.orders if o.symbol == symbol]

    def order_check(self, request):
        self._rec("order_check", request=dict(request))
        return Obj(retcode=0, margin=10.0, margin_free=990.0,
                   margin_level=9900.0, comment="fake-ok")

    def order_send(self, request):
        self._rec("order_send", request=dict(request))
        return Obj(retcode=self.TRADE_RETCODE_DONE, order=999, deal=999,
                   price=request.get("price", 0.0),
                   volume=request.get("volume", 0.0), comment="fake")

    def copy_rates_from_pos(self, symbol, timeframe, start, count):
        self._rec("copy_rates_from_pos", symbol=symbol, timeframe=timeframe)
        return list(self.rates)

    def history_deals_get(self, *a, **kw):
        self._rec("history_deals_get")
        return []
