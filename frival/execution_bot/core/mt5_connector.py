"""
MetaTrader5 Connector for MT5 Order Execution Bot

Handles MT5 connection management, authentication, and basic operations
based on DeafAgent commons.py MT5 integration patterns.
"""

import logging
import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import pytz

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

class MT5ConnectionError(Exception):
    """Custom exception for MT5 connection issues."""
    pass

class MT5Connector:
    """
    Manages MetaTrader5 connection and basic operations.
    
    Based on DeafAgent commons.py MT5 integration with enhanced
    error handling and connection management.
    """
    
    def __init__(self, config_manager):
        """
        Initialize MT5 connector.
        
        Args:
            config_manager: ConfigManager instance with credentials
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        self.connected = False
        self.login_info = None
        
        # Get credentials and settings
        self.credentials = config_manager.get_mt5_credentials()
        self.mt5_config = config_manager.get_config('mt5')
        
        # Connection parameters
        self.login = int(self.credentials['mt5_login'])
        self.password = self.credentials['mt5_password']
        self.server = self.credentials['mt5_server']
        self.terminal_path = self.credentials['mt5_terminal_path']
        
        # Timeout and retry settings
        self.timeout = self.mt5_config.get('timeout_seconds', 30)
        self.max_retries = self.mt5_config.get('max_retries', 3)
        self.retry_delay = self.mt5_config.get('retry_delay_seconds', 5)
        
        # Market timezone (from commons.py)
        timezone_str = self.mt5_config.get('market_timezone', 'Asia/Qatar')
        self.market_tz = pytz.timezone(timezone_str)
        
        # Check MT5 availability
        if not MT5_AVAILABLE:
            raise ImportError("MetaTrader5 package not available. Install with: pip install MetaTrader5")
    
    def connect(self) -> bool:
        """
        Establish connection to MetaTrader5.
        
        Returns:
            bool: True if connection successful, False otherwise
            
        Raises:
            MT5ConnectionError: If connection fails after retries
        """
        if self.connected:
            self.logger.info("Already connected to MT5")
            return True
        
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"Attempting MT5 connection (attempt {attempt + 1}/{self.max_retries})")
                
                # Initialize MT5 terminal
                if not mt5.initialize(path=self.terminal_path):
                    error_code = mt5.last_error()
                    self.logger.error(f"MT5 initialize() failed, error code: {error_code}")
                    
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        raise MT5ConnectionError(f"Failed to initialize MT5 after {self.max_retries} attempts")
                
                # Login to trading account
                if not mt5.login(self.login, self.password, self.server):
                    error_code = mt5.last_error()
                    self.logger.error(f"MT5 login failed, error code: {error_code}")
                    
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        raise MT5ConnectionError(f"Failed to login to MT5 after {self.max_retries} attempts")
                
                # Verify connection and get account info
                self.login_info = mt5.account_info()
                if self.login_info is None:
                    self.logger.error("Failed to get account info after login")
                    
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        raise MT5ConnectionError("Failed to verify account info")
                
                self.connected = True
                self.logger.info(f"Successfully connected to MT5 - Account: {self.login}, Server: {self.server}")
                self.logger.info(f"Account Info - Balance: {self.login_info.balance}, Equity: {self.login_info.equity}")
                
                return True
                
            except Exception as e:
                self.logger.error(f"Connection attempt {attempt + 1} failed: {str(e)}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise MT5ConnectionError(f"Failed to connect to MT5: {str(e)}")
        
        return False
    
    def disconnect(self):
        """Disconnect from MetaTrader5."""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            self.login_info = None
            self.logger.info("Disconnected from MT5")
    
    def validate_connection(self) -> bool:
        """
        Validate current MT5 connection.
        
        Returns:
            bool: True if connection is valid, False otherwise
        """
        if not self.connected:
            return False
        
        try:
            # Test connection by getting account info
            account_info = mt5.account_info()
            if account_info is None:
                self.logger.warning("Connection validation failed - no account info")
                self.connected = False
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Connection validation failed: {str(e)}")
            self.connected = False
            return False
    
    def reconnect(self) -> bool:
        """
        Reconnect to MetaTrader5.
        
        Returns:
            bool: True if reconnection successful, False otherwise
        """
        self.logger.info("Attempting to reconnect to MT5")
        self.disconnect()
        return self.connect()
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """
        Get current account information.
        
        Returns:
            Dict with account information or None if failed
        """
        if not self.validate_connection():
            self.logger.error("Cannot get account info - not connected")
            return None
        
        try:
            account_info = mt5.account_info()
            if account_info is None:
                self.logger.error("Failed to get account info")
                return None
            
            return {
                'login': account_info.login,
                'balance': account_info.balance,
                'equity': account_info.equity,
                'margin': account_info.margin,
                'margin_free': account_info.margin_free,
                'margin_level': account_info.margin_level,
                'leverage': account_info.leverage,
                'currency': account_info.currency,
                'server': account_info.server,
                'company': account_info.company
            }
            
        except Exception as e:
            self.logger.error(f"Error getting account info: {str(e)}")
            return None
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get symbol information.
        
        Args:
            symbol: Trading symbol (e.g., 'EURUSD')
            
        Returns:
            Dict with symbol information or None if failed
        """
        if not self.validate_connection():
            self.logger.error("Cannot get symbol info - not connected")
            return None
        
        try:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                self.logger.error(f"Symbol not found: {symbol}")
                return None
            
            return {
                'symbol': symbol_info.name,
                'description': symbol_info.description,
                'point': symbol_info.point,
                'digits': symbol_info.digits,
                'spread': symbol_info.spread,
                'volume_min': symbol_info.volume_min,
                'volume_max': symbol_info.volume_max,
                'volume_step': symbol_info.volume_step,
                'trade_mode': symbol_info.trade_mode,
                'margin_initial': symbol_info.margin_initial,
                'margin_maintenance': symbol_info.margin_maintenance
            }
            
        except Exception as e:
            self.logger.error(f"Error getting symbol info for {symbol}: {str(e)}")
            return None
    
    def get_symbol_tick(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current tick information for symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dict with tick information or None if failed
        """
        if not self.validate_connection():
            self.logger.error("Cannot get tick info - not connected")
            return None
        
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                self.logger.error(f"Failed to get tick for symbol: {symbol}")
                return None
            
            # Convert timestamp to datetime
            tick_time = datetime.fromtimestamp(tick.time, self.market_tz)
            
            return {
                'symbol': symbol,
                'time': tick_time,
                'bid': tick.bid,
                'ask': tick.ask,
                'last': tick.last,
                'volume': tick.volume,
                'spread': tick.ask - tick.bid
            }
            
        except Exception as e:
            self.logger.error(f"Error getting tick for {symbol}: {str(e)}")
            return None
    
    def get_positions(self, symbol: str = None) -> Optional[list]:
        """
        Get open positions.
        
        Args:
            symbol: Filter by symbol (optional)
            
        Returns:
            List of positions or None if failed
        """
        if not self.validate_connection():
            self.logger.error("Cannot get positions - not connected")
            return None
        
        try:
            if symbol:
                positions = mt5.positions_get(symbol=symbol)
            else:
                positions = mt5.positions_get()
            
            if positions is None:
                return []
            
            position_list = []
            for pos in positions:
                position_list.append({
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': pos.type,
                    'volume': pos.volume,
                    'price_open': pos.price_open,
                    'price_current': pos.price_current,
                    'profit': pos.profit,
                    'swap': pos.swap,
                    'comment': pos.comment,
                    'time': datetime.fromtimestamp(pos.time, self.market_tz)
                })
            
            return position_list
            
        except Exception as e:
            self.logger.error(f"Error getting positions: {str(e)}")
            return None
    
    def is_market_open(self, symbol: str) -> bool:
        """
        Check if market is open for trading.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            bool: True if market is open, False otherwise
        """
        try:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return False
            
            # Check if symbol is available for trading
            return symbol_info.trade_mode != mt5.SYMBOL_TRADE_MODE_DISABLED
            
        except Exception as e:
            self.logger.error(f"Error checking market status for {symbol}: {str(e)}")
            return False
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
