# MT5 Order Execution Bot — Core Package (adapted from DeafAgent demo_bot)
__version__ = "1.0.0"
from .mt5_connector import MT5Connector, MT5ConnectionError
from .order_manager import OrderManager, OrderValidationError, OrderExecutionError
from .config_manager import ConfigManager
__all__ = ['MT5Connector', 'OrderManager', 'ConfigManager']
