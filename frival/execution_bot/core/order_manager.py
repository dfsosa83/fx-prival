"""
Order Manager for MT5 Order Execution Bot

Handles order execution, validation, and position sizing based on
DeafAgent commons.py sendOrder() function and related logic.
Enhanced with SL/TP support and price tolerance logic.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import time

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

class OrderValidationError(Exception):
    """Custom exception for order validation issues."""
    pass

class OrderExecutionError(Exception):
    """Custom exception for order execution issues."""
    pass

class OrderManager:
    """
    Manages order execution and validation.
    
    Based on DeafAgent commons.py sendOrder() function with enhanced
    validation, error handling, and position sizing logic.
    """
    
    def __init__(self, mt5_connector, config_manager):
        """
        Initialize order manager.
        
        Args:
            mt5_connector: MT5Connector instance
            config_manager: ConfigManager instance
        """
        self.mt5_connector = mt5_connector
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # Get configuration
        self.trading_config = config_manager.get_trading_config()
        self.risk_config = config_manager.get_risk_config()
        self.order_config = config_manager.get_order_config()
        
        # Risk factors from commons.py
        self.risk_factors = self.risk_config.get('factors', {})
        self.scale_factors = self.risk_config.get('scale_factors', {})
        
        # Cache for symbol info to avoid repeated calls
        self.symbol_cache = {}

        # Price tolerance settings (pips)
        self.default_tolerance_pips = 5
        self.tolerance_by_symbol = {
            'EURUSD': 5,
            'GBPUSD': 6,
            'USDJPY': 5,
            'USDCHF': 4,
            'USDCAD': 5,
            'AUDUSD': 6,
            'NZDUSD': 6
        }

        # Pending order timeout (minutes)
        self.default_timeout_minutes = 10
        
    def execute_order(self, order_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a trading order with full validation.
        
        Args:
            order_params: Order parameters dictionary
            
        Returns:
            Dict with execution result
            
        Raises:
            OrderValidationError: If order validation fails
            OrderExecutionError: If order execution fails
        """
        try:
            # Validate order parameters
            self._validate_order(order_params)
            
            # Check emergency stop
            if self.config_manager.is_emergency_stop():
                raise OrderExecutionError("Emergency stop is active - no orders allowed")
            
            # Prepare order for execution
            prepared_order = self._prepare_order(order_params)
            
            # Execute the order
            result = self._send_order(prepared_order)
            
            # Log execution
            self._log_order_execution(prepared_order, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Order execution failed: {str(e)}")
            raise
    
    def _validate_order(self, order_params: Dict[str, Any]):
        """
        Validate order parameters before execution.
        
        Args:
            order_params: Order parameters to validate
            
        Raises:
            OrderValidationError: If validation fails
        """
        # Check required parameters
        required_fields = ['symbol', 'action', 'lot_size']
        for field in required_fields:
            if field not in order_params:
                raise OrderValidationError(f"Missing required field: {field}")
        
        symbol = order_params['symbol']
        action = order_params['action']
        lot_size = order_params['lot_size']
        
        # Validate action
        if action not in ['buy', 'sell']:
            raise OrderValidationError(f"Invalid action: {action}. Must be 'buy' or 'sell'")
        
        # Validate symbol
        symbol_info = self._get_symbol_info(symbol)
        if not symbol_info:
            raise OrderValidationError(f"Invalid or unavailable symbol: {symbol}")
        
        # Validate lot size
        min_lot = symbol_info['volume_min']
        max_lot = symbol_info['volume_max']
        
        if lot_size < min_lot:
            raise OrderValidationError(f"Lot size {lot_size} below minimum {min_lot}")
        
        if lot_size > max_lot:
            raise OrderValidationError(f"Lot size {lot_size} above maximum {max_lot}")
        
        # Check if market is open
        if not self.mt5_connector.is_market_open(symbol):
            raise OrderValidationError(f"Market is closed for symbol: {symbol}")
        
        # Check for existing positions (from commons.py logic)
        if self.trading_config.get('max_positions_per_symbol', 1) == 1:
            existing_positions = self.mt5_connector.get_positions(symbol)
            if existing_positions:
                for pos in existing_positions:
                    if (pos['type'] == mt5.POSITION_TYPE_BUY and action == 'buy') or \
                       (pos['type'] == mt5.POSITION_TYPE_SELL and action == 'sell'):
                        raise OrderValidationError(f"Position already exists for {symbol} {action}")
        
        # Validate account balance and margin
        self._validate_margin_requirements(symbol, lot_size, action)
    
    def _prepare_order(self, order_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare order for execution with position sizing and price calculations.
        
        Args:
            order_params: Raw order parameters
            
        Returns:
            Prepared order dictionary
        """
        symbol = order_params['symbol']
        action = order_params['action']
        
        # Get symbol information
        symbol_info = self._get_symbol_info(symbol)
        tick_info = self.mt5_connector.get_symbol_tick(symbol)
        
        if not tick_info:
            raise OrderExecutionError(f"Failed to get current price for {symbol}")
        
        # Calculate position size (based on commons.py logic)
        lot_size = self._calculate_position_size(order_params, symbol_info)
        
        # Handle entry price and price tolerance logic
        entry_price = order_params.get('entry_price')
        tolerance_pips = order_params.get('tolerance_pips', self.get_tolerance_pips(symbol))
        current_price = tick_info['ask'] if action == 'buy' else tick_info['bid']

        # Determine order type and price based on entry price and tolerance
        order_type = order_params.get('order_type', 'MARKET')

        if entry_price is not None:
            # Check if current price is within tolerance of entry price
            if self.is_price_within_tolerance(current_price, entry_price, symbol, tolerance_pips):
                # Execute as market order
                order_type = 'MARKET'
                price = current_price
                self.logger.info(f"Price within tolerance ({tolerance_pips} pips) - executing market order")
            else:
                # Execute as pending order
                order_type = 'PENDING'
                price = entry_price
                pip_diff = abs(current_price - entry_price) / self.get_pip_value(symbol)
                self.logger.info(f"Price outside tolerance ({pip_diff:.1f} pips) - placing pending order")
        else:
            # No entry price specified, use current market price
            price = current_price

        # Prepare MT5 order request (based on commons.py sendOrder function)
        mt5_order_type = mt5.ORDER_TYPE_BUY if action == 'buy' else mt5.ORDER_TYPE_SELL
        
        # Handle different order types
        if order_type == 'PENDING':
            # Determine pending order type based on current vs entry price
            pending_type = self.determine_pending_order_type(action, current_price, price)

            if pending_type == 'BUY_LIMIT':
                mt5_order_type = mt5.ORDER_TYPE_BUY_LIMIT
            elif pending_type == 'BUY_STOP':
                mt5_order_type = mt5.ORDER_TYPE_BUY_STOP
            elif pending_type == 'SELL_LIMIT':
                mt5_order_type = mt5.ORDER_TYPE_SELL_LIMIT
            elif pending_type == 'SELL_STOP':
                mt5_order_type = mt5.ORDER_TYPE_SELL_STOP

        elif order_type == 'STOP':
            stop_distance = order_params.get('stop_order_dist_pips', 2)
            pip_value = self._pips_to_price(stop_distance, symbol_info)

            if action == 'buy':
                price = tick_info['ask'] + pip_value
                mt5_order_type = mt5.ORDER_TYPE_BUY_STOP
            else:
                price = tick_info['bid'] - pip_value
                mt5_order_type = mt5.ORDER_TYPE_SELL_STOP

        elif order_type == 'LIMIT':
            limit_distance = order_params.get('limit_order_dist_pips', 2)
            pip_value = self._pips_to_price(limit_distance, symbol_info)

            if action == 'buy':
                price = tick_info['ask'] - pip_value
                mt5_order_type = mt5.ORDER_TYPE_BUY_LIMIT
            else:
                price = tick_info['bid'] + pip_value
                mt5_order_type = mt5.ORDER_TYPE_SELL_LIMIT
        
        # Round price to symbol digits
        price = round(price, symbol_info['digits'])
        
        # Handle Stop Loss and Take Profit
        stop_loss = order_params.get('stop_loss')
        take_profit = order_params.get('take_profit')

        # Validate SL/TP levels if provided
        if stop_loss is not None or take_profit is not None:
            validation = self.validate_sl_tp_levels(action, price, stop_loss, take_profit)
            if not validation['valid']:
                raise OrderValidationError(f"Invalid SL/TP levels: {validation['errors']}")

            # Log warnings if any
            for warning in validation['warnings']:
                self.logger.warning(warning)

        # Prepare the order request
        prepared_order = {
            'action': mt5.TRADE_ACTION_DEAL if order_type == 'MARKET' else mt5.TRADE_ACTION_PENDING,
            'symbol': symbol,
            'volume': lot_size,
            'type': mt5_order_type,
            'price': price,
            'deviation': order_params.get('deviation_points', 30),
            'comment': order_params.get('comment', 'DeafAgent Bot'),
            'type_time': mt5.ORDER_TIME_GTC,
            'type_filling': order_params.get('filling_type', mt5.ORDER_FILLING_IOC)
        }

        # Add Stop Loss if specified
        if stop_loss is not None:
            prepared_order['sl'] = round(stop_loss, symbol_info['digits'])

        # Add Take Profit if specified
        if take_profit is not None:
            prepared_order['tp'] = round(take_profit, symbol_info['digits'])

        # 🛡️ CRITICAL SAFETY CHECK: Validate SL/TP are present
        sl_in_order = 'sl' in prepared_order
        tp_in_order = 'tp' in prepared_order

        if not sl_in_order or not tp_in_order:
            missing_levels = []
            if not sl_in_order:
                missing_levels.append("Stop Loss")
            if not tp_in_order:
                missing_levels.append("Take Profit")

            error_msg = f"Order blocked: Missing {' and '.join(missing_levels)} levels"
            self.logger.error(f"🚨 SAFETY BLOCK: {error_msg}")
            self.logger.error(f"Symbol: {symbol}, Action: {action}, Lot Size: {lot_size}")
            self.logger.error(f"SL Present: {sl_in_order}, TP Present: {tp_in_order}")

            raise OrderValidationError(f"🛡️ SAFETY CONTROL: {error_msg}. All orders must have both SL and TP levels.")
        
        # Add expiration for pending orders
        if order_type == 'PENDING':
            timeout_minutes = order_params.get('timeout_minutes', self.default_timeout_minutes)
            expiration_secs = timeout_minutes * 60
            prepared_order['type_time'] = mt5.ORDER_TIME_SPECIFIED
            # tick_info['time'] is already a datetime object, convert to timestamp
            current_timestamp = tick_info['time'].timestamp()
            prepared_order['expiration'] = int(current_timestamp + expiration_secs)
            self.logger.info(f"Pending order will expire in {timeout_minutes} minutes")
        else:
            # Market orders don't need expiration - only add for limit/stop orders
            if order_type in ['LIMIT', 'STOP']:
                expiration_secs = order_params.get('expiration_seconds', 0)
                if expiration_secs > 0:
                    prepared_order['type_time'] = mt5.ORDER_TIME_SPECIFIED
                    # tick_info['time'] is already a datetime object, convert to timestamp
                    current_timestamp = tick_info['time'].timestamp()
                    prepared_order['expiration'] = int(current_timestamp + expiration_secs)
        
        return prepared_order
    
    def _calculate_position_size(self, order_params: Dict[str, Any], symbol_info: Dict[str, Any]) -> float:
        """
        Calculate position size based on risk profile and account balance.
        
        Based on commons.py calcPositionSize functions.
        
        Args:
            order_params: Order parameters
            symbol_info: Symbol information
            
        Returns:
            Calculated lot size
        """
        # Get base lot size
        base_lot_size = order_params.get('lot_size', self.trading_config.get('default_lot_size', 0.8))
        
        # Check if dynamic sizing is enabled
        if not order_params.get('dynamic_sizing', True):
            return base_lot_size
        
        # Get risk profile
        risk_profile = order_params.get('risk_profile', self.trading_config.get('default_risk_profile', 'MODERATE'))
        
        # Get account information
        account_info = self.mt5_connector.get_account_info()
        if not account_info:
            self.logger.warning("Could not get account info for position sizing, using base lot size")
            return base_lot_size
        
        # Calculate position size based on risk profile
        balance = account_info['balance']
        leverage = account_info['leverage']
        
        # Get risk factor
        risk_factor = self.risk_factors.get(risk_profile.lower(), 0.1)
        scale_factor = self.scale_factors.get(risk_profile.lower(), 1.0)
        
        # Calculate maximum available lots
        max_lots_available = self._calculate_max_lots(symbol_info['symbol'], account_info)
        
        # Apply risk-based sizing
        risk_adjusted_size = base_lot_size * scale_factor

        # Apply signal strength scaling (NEW FEATURE)
        signal_strength = order_params.get('signal_strength', 75)
        signal_tier = order_params.get('signal_tier', 'normal')

        # Signal strength multipliers
        signal_multipliers = {
            'weak': 0.5,      # Reduce lot size for weak signals
            'normal': 1.0,    # Standard lot size
            'strong': 1.5,    # Increase for strong signals
            'golden': 2.0     # Maximum increase for golden signals
        }

        signal_multiplier = signal_multipliers.get(signal_tier.lower(), 1.0)
        risk_adjusted_size *= signal_multiplier

        # Apply balance percentage with proper risk calculation
        balance_perc = order_params.get('balance_percentage', 1.0)
        if balance_perc != 1.0:
            # Calculate risk as percentage of balance (much safer)
            max_risk_amount = balance * (balance_perc / 100)  # Convert to percentage
            # Estimate position value (simplified)
            estimated_position_value = risk_adjusted_size * 100000  # Standard lot value
            if estimated_position_value > max_risk_amount:
                risk_adjusted_size = max_risk_amount / 100000
                self.logger.info(f"Lot size reduced due to balance percentage limit: {balance_perc}%")
        
        # Ensure within limits
        min_lot = symbol_info['volume_min']
        max_lot = min(symbol_info['volume_max'], max_lots_available)
        
        final_lot_size = max(min(risk_adjusted_size, max_lot), min_lot)
        final_lot_size = round(final_lot_size, 2)
        
        self.logger.info(f"Position sizing: Base={base_lot_size}, Risk={risk_profile}, "
                        f"Signal={signal_tier}({signal_multiplier}x), Final={final_lot_size}, "
                        f"Available={max_lots_available}")
        
        return final_lot_size
    
    def _calculate_max_lots(self, symbol: str, account_info: Dict[str, Any]) -> float:
        """
        Calculate maximum available lots based on margin.
        
        Based on commons.py calcMaxLots function.
        
        Args:
            symbol: Trading symbol
            account_info: Account information
            
        Returns:
            Maximum available lot size
        """
        try:
            # Get current price for margin calculation
            tick_info = self.mt5_connector.get_symbol_tick(symbol)
            if not tick_info:
                return 1.0  # Default fallback
            
            price = tick_info['ask']  # Use ask price for margin calculation
            
            # Calculate margin requirement for 1 lot
            margin_rate = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, symbol, 1.0, price)
            
            if margin_rate and margin_rate > 0:
                max_lots = account_info['margin_free'] / margin_rate
                return max(0.01, max_lots)  # Ensure minimum 0.01
            else:
                self.logger.warning(f"Could not calculate margin rate for {symbol}")
                return 1.0  # Default fallback
                
        except Exception as e:
            self.logger.error(f"Error calculating max lots for {symbol}: {str(e)}")
            return 1.0  # Default fallback
    
    def _validate_margin_requirements(self, symbol: str, lot_size: float, action: str):
        """
        Validate margin requirements for the order.
        
        Args:
            symbol: Trading symbol
            lot_size: Lot size
            action: Order action (buy/sell)
            
        Raises:
            OrderValidationError: If insufficient margin
        """
        account_info = self.mt5_connector.get_account_info()
        if not account_info:
            raise OrderValidationError("Cannot validate margin - account info unavailable")
        
        tick_info = self.mt5_connector.get_symbol_tick(symbol)
        if not tick_info:
            raise OrderValidationError("Cannot validate margin - price info unavailable")
        
        price = tick_info['ask'] if action == 'buy' else tick_info['bid']
        order_type = mt5.ORDER_TYPE_BUY if action == 'buy' else mt5.ORDER_TYPE_SELL
        
        # Calculate required margin
        required_margin = mt5.order_calc_margin(order_type, symbol, lot_size, price)
        
        if required_margin is None:
            self.logger.warning("Could not calculate required margin")
            return  # Skip validation if calculation fails
        
        available_margin = account_info['margin_free']
        
        if required_margin > available_margin:
            raise OrderValidationError(
                f"Insufficient margin: Required {required_margin}, Available {available_margin}"
            )
    
    def _send_order(self, order_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send order to MetaTrader5.
        
        Args:
            order_request: Prepared order request
            
        Returns:
            Order execution result
            
        Raises:
            OrderExecutionError: If order execution fails
        """
        if not self.mt5_connector.validate_connection():
            raise OrderExecutionError("MT5 connection not available")
        
        # Check demo mode
        if self.config_manager.is_demo_mode():
            self.logger.info("DEMO MODE: Order would be executed with parameters:")
            for key, value in order_request.items():
                self.logger.info(f"  {key}: {value}")
            
            # Return simulated success result
            return {
                'success': True,
                'retcode': mt5.TRADE_RETCODE_DONE,
                'order': 0,  # Dummy order ID
                'deal': 0,   # Dummy deal ID
                'volume': order_request['volume'],
                'price': order_request['price'],
                'comment': 'DEMO MODE - Simulated execution',
                'request_id': 0
            }
        
        # Execute real order
        try:
            # Ensure symbol is selected before sending order
            symbol = order_request['symbol']
            if not mt5.symbol_select(symbol, True):
                raise OrderExecutionError(f"Failed to select symbol {symbol}")

            result = mt5.order_send(order_request)

            # Check if result is None (common issue)
            if result is None:
                error_code = mt5.last_error()
                raise OrderExecutionError(f"order_send() returned None. MT5 error: {error_code}")

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                error_msg = f"Order failed with retcode: {result.retcode}"
                self.logger.error(error_msg)
                
                # Log detailed error information
                result_dict = result._asdict()
                for field, value in result_dict.items():
                    self.logger.error(f"  {field}: {value}")
                
                raise OrderExecutionError(error_msg)
            
            # Return success result
            return {
                'success': True,
                'retcode': result.retcode,
                'order': result.order,
                'deal': result.deal,
                'volume': result.volume,
                'price': result.price,
                'comment': result.comment,
                'request_id': result.request_id
            }
            
        except Exception as e:
            raise OrderExecutionError(f"Order execution failed: {str(e)}")
    
    def _get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get symbol information with caching."""
        if symbol not in self.symbol_cache:
            self.symbol_cache[symbol] = self.mt5_connector.get_symbol_info(symbol)
        return self.symbol_cache[symbol]
    
    def _pips_to_price(self, pips: float, symbol_info: Dict[str, Any]) -> float:
        """
        Convert pips to price value.
        
        Args:
            pips: Number of pips
            symbol_info: Symbol information
            
        Returns:
            Price value equivalent to pips
        """
        point = symbol_info['point']
        digits = symbol_info['digits']
        
        # Calculate pip multiplier (from commons.py)
        pnt_multiplier = pow(10, digits)
        pip_multiplier = pnt_multiplier / 10
        
        return pips / pip_multiplier
    
    def _log_order_execution(self, order_request: Dict[str, Any], result: Dict[str, Any]):
        """Log order execution details."""
        symbol = order_request['symbol']
        volume = order_request['volume']
        price = order_request['price']
        action = "BUY" if order_request['type'] in [mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_BUY_STOP] else "SELL"
        
        if result['success']:
            self.logger.info(f"Order executed successfully: {action} {volume} lots of {symbol} at {price}")
            if not self.config_manager.is_demo_mode():
                self.logger.info(f"Order ID: {result['order']}, Deal ID: {result['deal']}")
        else:
            self.logger.error(f"Order execution failed: {action} {volume} lots of {symbol} at {price}")
    
    def get_order_history(self, days: int = 7) -> Optional[list]:
        """
        Get order history for specified number of days.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of historical orders or None if failed
        """
        if not self.mt5_connector.validate_connection():
            return None
        
        try:
            from_date = datetime.now() - timedelta(days=days)
            to_date = datetime.now()
            
            deals = mt5.history_deals_get(from_date, to_date)
            
            if deals is None:
                return []
            
            deal_list = []
            for deal in deals:
                deal_list.append({
                    'ticket': deal.ticket,
                    'order': deal.order,
                    'symbol': deal.symbol,
                    'type': deal.type,
                    'volume': deal.volume,
                    'price': deal.price,
                    'profit': deal.profit,
                    'swap': deal.swap,
                    'commission': deal.commission,
                    'comment': deal.comment,
                    'time': datetime.fromtimestamp(deal.time)
                })
            
            return deal_list
            
        except Exception as e:
            self.logger.error(f"Error getting order history: {str(e)}")
            return None

    def close_position(self, ticket: int) -> Dict[str, Any]:
        """
        Close an open position.

        Args:
            ticket: Position ticket number

        Returns:
            Close result dictionary
        """
        if not self.mt5_connector.validate_connection():
            raise OrderExecutionError("MT5 connection not available")

        try:
            # Get position info
            positions = mt5.positions_get(ticket=ticket)
            if not positions:
                raise OrderExecutionError(f"Position {ticket} not found")

            position = positions[0]

            # Prepare close request
            close_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                "position": ticket,
                "comment": "Position closed by bot",
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            # Execute close order
            if self.config_manager.is_demo_mode():
                self.logger.info(f"DEMO MODE: Would close position {ticket}")
                return {'success': True, 'comment': 'DEMO MODE - Simulated close'}

            result = mt5.order_send(close_request)

            if result.retcode != mt5.TRADE_RETCODE_DONE:
                raise OrderExecutionError(f"Failed to close position {ticket}: {result.retcode}")

            self.logger.info(f"Position {ticket} closed successfully")
            return {'success': True, 'deal': result.deal}

        except Exception as e:
            self.logger.error(f"Error closing position {ticket}: {str(e)}")
            raise

    # ============================================================================
    # Price Tolerance and SL/TP Methods
    # ============================================================================

    def get_pip_value(self, symbol: str) -> float:
        """
        Get pip value for a currency pair.

        Args:
            symbol: Currency pair symbol (e.g., 'EURUSD', 'USDJPY')

        Returns:
            Pip value as float
        """
        if 'JPY' in symbol.upper():
            return 0.01  # JPY pairs have 2 decimal places
        else:
            return 0.0001  # Most major pairs have 4 decimal places

    def get_tolerance_pips(self, symbol: str) -> int:
        """
        Get tolerance in pips for a specific symbol.

        Args:
            symbol: Currency pair symbol

        Returns:
            Tolerance in pips
        """
        return self.tolerance_by_symbol.get(symbol.upper(), self.default_tolerance_pips)

    def calculate_price_tolerance(self, symbol: str, tolerance_pips: Optional[int] = None) -> float:
        """
        Calculate price tolerance in price units.

        Args:
            symbol: Currency pair symbol
            tolerance_pips: Number of pips tolerance (uses default if None)

        Returns:
            Tolerance in price units
        """
        if tolerance_pips is None:
            tolerance_pips = self.get_tolerance_pips(symbol)

        pip_value = self.get_pip_value(symbol)
        return tolerance_pips * pip_value

    def is_price_within_tolerance(self, current_price: float, target_price: float,
                                 symbol: str, tolerance_pips: Optional[int] = None) -> bool:
        """
        Check if current price is within tolerance of target price.

        Args:
            current_price: Current market price
            target_price: Target entry price
            symbol: Currency pair symbol
            tolerance_pips: Number of pips tolerance (uses default if None)

        Returns:
            True if within tolerance, False otherwise
        """
        tolerance = self.calculate_price_tolerance(symbol, tolerance_pips)
        price_diff = abs(current_price - target_price)
        return price_diff <= tolerance

    def determine_pending_order_type(self, action: str, current_price: float, entry_price: float) -> str:
        """
        Determine the appropriate pending order type.

        Args:
            action: 'buy' or 'sell'
            current_price: Current market price
            entry_price: Desired entry price

        Returns:
            Order type string ('BUY_LIMIT', 'BUY_STOP', 'SELL_LIMIT', 'SELL_STOP')
        """
        if action.lower() == 'buy':
            if current_price > entry_price:
                return 'BUY_LIMIT'   # Buy when price comes down
            else:
                return 'BUY_STOP'    # Buy when price goes up
        else:  # sell
            if current_price < entry_price:
                return 'SELL_LIMIT'  # Sell when price comes up
            else:
                return 'SELL_STOP'   # Sell when price goes down

    def validate_sl_tp_levels(self, action: str, entry_price: float,
                             stop_loss: Optional[float], take_profit: Optional[float]) -> Dict[str, Any]:
        """
        Validate Stop Loss and Take Profit levels.

        Args:
            action: 'buy' or 'sell'
            entry_price: Entry price
            stop_loss: Stop loss price (optional)
            take_profit: Take profit price (optional)

        Returns:
            Dict with validation results
        """
        validation = {
            'valid': True,
            'errors': [],
            'warnings': []
        }

        if stop_loss is not None:
            if action.lower() == 'buy':
                if stop_loss >= entry_price:
                    validation['errors'].append(f"BUY order: Stop Loss ({stop_loss}) should be below entry price ({entry_price})")
                    validation['valid'] = False
            else:  # sell
                if stop_loss <= entry_price:
                    validation['errors'].append(f"SELL order: Stop Loss ({stop_loss}) should be above entry price ({entry_price})")
                    validation['valid'] = False

        if take_profit is not None:
            if action.lower() == 'buy':
                if take_profit <= entry_price:
                    validation['errors'].append(f"BUY order: Take Profit ({take_profit}) should be above entry price ({entry_price})")
                    validation['valid'] = False
            else:  # sell
                if take_profit >= entry_price:
                    validation['errors'].append(f"SELL order: Take Profit ({take_profit}) should be below entry price ({entry_price})")
                    validation['valid'] = False

        return validation
