"""
Utility functions for MT5 Order Execution Bot

Common utility functions and helpers based on DeafAgent commons.py patterns.
"""

import logging
import os
import json
from typing import Dict, Any, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path
import MetaTrader5 as mt5

def print_colored(text: str, color: str = "white"):
    """
    Print colored text to console (simplified version from commons.py).
    
    Args:
        text: Text to print
        color: Color name (for compatibility, actual coloring not implemented)
    """
    # Simplified version - just print with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {text}")

def setup_logging(log_dir: str = "logs", log_level: str = "INFO") -> logging.Logger:
    """
    Setup comprehensive logging configuration.
    
    Args:
        log_dir: Directory for log files
        log_level: Logging level
        
    Returns:
        Configured logger
    """
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Configure logging level
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handlers
    file_handlers = {
        'main': log_path / 'bot_activity.log',
        'orders': log_path / 'orders.log',
        'errors': log_path / 'errors.log',
        'security': log_path / 'security.log'
    }
    
    for handler_name, log_file in file_handlers.items():
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(detailed_formatter)
        
        # Create specific logger for each category
        category_logger = logging.getLogger(handler_name)
        category_logger.addHandler(file_handler)
        category_logger.setLevel(level)
    
    return root_logger

def validate_symbol_format(symbol: str) -> bool:
    """
    Validate trading symbol format.
    
    Args:
        symbol: Trading symbol to validate
        
    Returns:
        bool: True if valid format, False otherwise
    """
    if not symbol or len(symbol) < 6:
        return False
    
    # Common forex pairs
    major_pairs = [
        'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'USDCAD', 'AUDUSD', 'NZDUSD'
    ]
    
    # Check if it's a known major pair
    if symbol.upper() in major_pairs:
        return True
    
    # Basic format validation (6-7 characters, all letters)
    return symbol.isalpha() and 6 <= len(symbol) <= 7

def calculate_pip_value(symbol: str, lot_size: float, account_currency: str = "USD") -> Optional[float]:
    """
    Calculate pip value for a given symbol and lot size.
    
    Args:
        symbol: Trading symbol
        lot_size: Position size in lots
        account_currency: Account currency
        
    Returns:
        Pip value in account currency or None if calculation fails
    """
    try:
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            return None
        
        # For most USD pairs, 1 pip = $10 per standard lot
        if symbol.endswith('USD') and account_currency == 'USD':
            return 10.0 * lot_size
        elif symbol.startswith('USD') and account_currency == 'USD':
            # For USD/XXX pairs, need current exchange rate
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                return (10.0 * lot_size) / tick.ask
        
        # Simplified calculation for other cases
        return 10.0 * lot_size
        
    except Exception:
        return None

def format_currency(amount: float, currency: str = "USD", decimals: int = 2) -> str:
    """
    Format currency amount for display.
    
    Args:
        amount: Amount to format
        currency: Currency code
        decimals: Number of decimal places
        
    Returns:
        Formatted currency string
    """
    return f"{amount:,.{decimals}f} {currency}"

def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format percentage for display.
    
    Args:
        value: Percentage value (0.05 = 5%)
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    return f"{value * 100:.{decimals}f}%"

def save_json_data(data: Dict[str, Any], file_path: str, backup: bool = True):
    """
    Save data to JSON file with optional backup.
    
    Args:
        data: Data to save
        file_path: Output file path
        backup: Whether to create backup of existing file
    """
    file_path = Path(file_path)
    
    # Create backup if file exists and backup is requested
    if backup and file_path.exists():
        backup_path = file_path.with_suffix(f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        file_path.rename(backup_path)
    
    # Ensure directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save data
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)

def load_json_data(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Load data from JSON file.
    
    Args:
        file_path: Input file path
        
    Returns:
        Loaded data or None if failed
    """
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def get_market_session(dt: datetime = None) -> str:
    """
    Determine current market session.
    
    Args:
        dt: Datetime to check (defaults to now)
        
    Returns:
        Market session name
    """
    if dt is None:
        dt = datetime.utcnow()
    
    hour = dt.hour
    
    # Simplified market sessions (UTC)
    if 22 <= hour or hour < 6:
        return "Sydney"
    elif 6 <= hour < 8:
        return "Tokyo"
    elif 8 <= hour < 16:
        return "London"
    elif 16 <= hour < 22:
        return "New York"
    else:
        return "Overlap"

def is_market_hours(symbol: str = None, dt: datetime = None) -> bool:
    """
    Check if market is open for trading.
    
    Args:
        symbol: Trading symbol (optional)
        dt: Datetime to check (defaults to now)
        
    Returns:
        bool: True if market is open, False otherwise
    """
    if dt is None:
        dt = datetime.utcnow()
    
    # Forex market is open 24/5
    weekday = dt.weekday()
    
    # Market closed on weekends
    if weekday == 5:  # Saturday
        return False
    elif weekday == 6:  # Sunday
        # Market opens Sunday 22:00 UTC
        return dt.hour >= 22
    else:
        # Market closes Friday 22:00 UTC
        if weekday == 4 and dt.hour >= 22:
            return False
        return True

def calculate_lot_size_from_risk(balance: float, risk_percent: float, stop_loss_pips: float, 
                                pip_value: float) -> float:
    """
    Calculate lot size based on risk percentage.
    
    Args:
        balance: Account balance
        risk_percent: Risk percentage (0.02 = 2%)
        stop_loss_pips: Stop loss distance in pips
        pip_value: Pip value per lot
        
    Returns:
        Calculated lot size
    """
    if stop_loss_pips <= 0 or pip_value <= 0:
        return 0.01  # Minimum lot size
    
    risk_amount = balance * risk_percent
    lot_size = risk_amount / (stop_loss_pips * pip_value)
    
    # Round to 2 decimal places and ensure minimum
    return max(0.01, round(lot_size, 2))

def validate_order_parameters(params: Dict[str, Any]) -> Dict[str, str]:
    """
    Validate order parameters and return any errors.
    
    Args:
        params: Order parameters to validate
        
    Returns:
        Dict of validation errors (empty if valid)
    """
    errors = {}
    
    # Required fields
    required_fields = ['symbol', 'action', 'lot_size']
    for field in required_fields:
        if field not in params or params[field] is None:
            errors[field] = f"Required field '{field}' is missing"
    
    # Validate action
    if 'action' in params and params['action'] not in ['buy', 'sell']:
        errors['action'] = "Action must be 'buy' or 'sell'"
    
    # Validate lot size
    if 'lot_size' in params:
        try:
            lot_size = float(params['lot_size'])
            if lot_size <= 0:
                errors['lot_size'] = "Lot size must be positive"
            elif lot_size > 100:  # Reasonable maximum
                errors['lot_size'] = "Lot size too large (max 100)"
        except (ValueError, TypeError):
            errors['lot_size'] = "Lot size must be a number"
    
    # Validate symbol
    if 'symbol' in params and not validate_symbol_format(params['symbol']):
        errors['symbol'] = "Invalid symbol format"
    
    return errors

def get_system_info() -> Dict[str, Any]:
    """
    Get system information for diagnostics.
    
    Returns:
        Dict with system information
    """
    import platform
    import psutil
    
    return {
        'platform': platform.platform(),
        'python_version': platform.python_version(),
        'cpu_count': psutil.cpu_count(),
        'memory_total': psutil.virtual_memory().total,
        'memory_available': psutil.virtual_memory().available,
        'disk_usage': psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:').percent,
        'mt5_available': True,  # We know it's available if we're running
        'timestamp': datetime.now().isoformat()
    }

def create_order_summary(order_params: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a summary of order execution for logging/reporting.
    
    Args:
        order_params: Original order parameters
        result: Execution result
        
    Returns:
        Order summary dictionary
    """
    return {
        'timestamp': datetime.now().isoformat(),
        'symbol': order_params.get('symbol'),
        'action': order_params.get('action'),
        'lot_size': order_params.get('lot_size'),
        'order_type': order_params.get('order_type', 'MARKET'),
        'success': result.get('success', False),
        'order_id': result.get('order'),
        'deal_id': result.get('deal'),
        'price': result.get('price'),
        'comment': result.get('comment'),
        'retcode': result.get('retcode')
    }

class PerformanceTimer:
    """Simple performance timer for measuring execution times."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def start(self):
        """Start the timer."""
        self.start_time = datetime.now()
    
    def stop(self):
        """Stop the timer."""
        self.end_time = datetime.now()
    
    def elapsed(self) -> Optional[timedelta]:
        """Get elapsed time."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
    
    def elapsed_ms(self) -> Optional[float]:
        """Get elapsed time in milliseconds."""
        elapsed = self.elapsed()
        return elapsed.total_seconds() * 1000 if elapsed else None
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
