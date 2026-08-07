"""
Configuration Manager for MT5 Order Execution Bot

Handles loading, validation, and management of configuration files
and environment variables based on DeafAgent patterns.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

class ConfigManager:
    """
    Manages configuration loading and validation for the MT5 bot.
    
    Based on DeafAgent commons.py configuration patterns with enhanced
    security and validation features.
    """
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self.config = {}
        self.credentials = {}
        self.logger = logging.getLogger(__name__)
        
        # Load configurations
        self._load_environment_variables()
        self._load_yaml_config()
        self._validate_configuration()
    
    def _load_environment_variables(self):
        """Load environment variables from .env file."""
        env_file = self.config_dir / "credentials.env"
        
        if env_file.exists():
            load_dotenv(env_file)
            self.logger.info(f"Loaded environment variables from {env_file}")
        else:
            self.logger.warning(f"Environment file not found: {env_file}")
            self.logger.info("Using system environment variables only")
        
        # Load MT5 credentials
        self.credentials = {
            'mt5_login': self._get_env_var('MT5_LOGIN', required=True),
            'mt5_password': self._get_env_var('MT5_PASSWORD', required=True),
            'mt5_server': self._get_env_var('MT5_SERVER', required=True),
            'mt5_terminal_path': self._get_env_var('MT5_TERMINAL_PATH', required=True),
            'demo_mode': self._get_env_bool('DEMO_MODE', default=True),
            'emergency_stop': self._get_env_bool('EMERGENCY_STOP', default=False),
            'log_level': self._get_env_var('LOG_LEVEL', default='INFO'),
            'max_daily_trades': self._get_env_int('MAX_DAILY_TRADES', default=50),
            'max_daily_loss': self._get_env_float('MAX_DAILY_LOSS', default=1000.0)
        }
    
    def _load_yaml_config(self):
        """Load main configuration from YAML file."""
        config_file = self.config_dir / "settings.yaml"
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        try:
            with open(config_file, 'r') as f:
                self.config = yaml.safe_load(f)
            self.logger.info(f"Loaded configuration from {config_file}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML configuration: {e}")
    
    def _validate_configuration(self):
        """Validate loaded configuration for required fields and formats."""
        # Validate MT5 credentials
        self._validate_mt5_credentials()
        
        # Validate trading configuration
        self._validate_trading_config()
        
        # Validate risk management settings
        self._validate_risk_config()
        
        # Apply environment overrides
        self._apply_environment_overrides()
        
        self.logger.info("Configuration validation completed successfully")
    
    def _validate_mt5_credentials(self):
        """Validate MT5 connection credentials."""
        login = self.credentials['mt5_login']
        password = self.credentials['mt5_password']
        server = self.credentials['mt5_server']
        terminal_path = self.credentials['mt5_terminal_path']
        
        # Validate login (should be 7-8 digits)
        if not login.isdigit() or len(login) < 7 or len(login) > 8:
            raise ValueError("MT5_LOGIN must be 7-8 digits")
        
        # Validate password strength
        if len(password) < 8:
            raise ValueError("MT5_PASSWORD must be at least 8 characters")
        
        # Validate server format (accept both old and new server names)
        valid_prefixes = ['FPMarketsLLC-', 'FPMarketsSC-']
        if not any(server.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError("MT5_SERVER must be FPMarketsLLC-* or FPMarketsSC-* (Demo/Live)")
        
        # Validate terminal path exists
        if not Path(terminal_path).exists():
            self.logger.warning(f"MT5 terminal path not found: {terminal_path}")
    
    def _validate_trading_config(self):
        """Validate trading configuration settings."""
        trading_config = self.config.get('trading', {})
        
        # Validate trading mode
        mode = trading_config.get('mode', 'demo')
        if mode not in ['demo', 'live']:
            raise ValueError("Trading mode must be 'demo' or 'live'")
        
        # Validate risk profile
        risk_profile = trading_config.get('default_risk_profile', 'MODERATE')
        valid_profiles = [
            'VERY_CONSERVATIVE', 'CONSERVATIVE', 'MODERATE', 
            'BALANCED', 'GROWTH', 'AGGRESSIVE', 'VERY_AGGRESSIVE'
        ]
        if risk_profile not in valid_profiles:
            raise ValueError(f"Risk profile must be one of: {valid_profiles}")
    
    def _validate_risk_config(self):
        """Validate risk management configuration."""
        risk_config = self.config.get('risk', {})
        
        # Validate lot sizes
        max_lot = risk_config.get('max_lot_size', 10.0)
        min_lot = risk_config.get('min_lot_size', 0.01)
        
        if max_lot <= min_lot:
            raise ValueError("max_lot_size must be greater than min_lot_size")
        
        if min_lot <= 0:
            raise ValueError("min_lot_size must be positive")
    
    def _apply_environment_overrides(self):
        """Apply environment variable overrides to configuration."""
        # Override risk profile if specified
        risk_override = os.getenv('RISK_PROFILE_OVERRIDE')
        if risk_override:
            self.config['trading']['default_risk_profile'] = risk_override
        
        # Override position sizes if specified
        max_pos_override = os.getenv('MAX_POSITION_SIZE')
        if max_pos_override:
            self.config['risk']['max_lot_size'] = float(max_pos_override)
        
        min_pos_override = os.getenv('MIN_POSITION_SIZE')
        if min_pos_override:
            self.config['risk']['min_lot_size'] = float(min_pos_override)
    
    def _get_env_var(self, key: str, default: Optional[str] = None, required: bool = False) -> str:
        """Get environment variable with validation."""
        value = os.getenv(key, default)
        if required and not value:
            raise ValueError(f"Required environment variable not set: {key}")
        return value
    
    def _get_env_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean environment variable."""
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    def _get_env_int(self, key: str, default: int = 0) -> int:
        """Get integer environment variable."""
        try:
            return int(os.getenv(key, str(default)))
        except ValueError:
            return default
    
    def _get_env_float(self, key: str, default: float = 0.0) -> float:
        """Get float environment variable."""
        try:
            return float(os.getenv(key, str(default)))
        except ValueError:
            return default
    
    def get_mt5_credentials(self) -> Dict[str, Any]:
        """Get MT5 connection credentials."""
        return self.credentials.copy()
    
    def get_trading_config(self) -> Dict[str, Any]:
        """Get trading configuration."""
        return self.config.get('trading', {})
    
    def get_risk_config(self) -> Dict[str, Any]:
        """Get risk management configuration."""
        return self.config.get('risk', {})
    
    def get_order_config(self) -> Dict[str, Any]:
        """Get order execution configuration."""
        return self.config.get('orders', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self.config.get('logging', {})
    
    def is_demo_mode(self) -> bool:
        """Check if running in demo mode."""
        return self.credentials.get('demo_mode', True)
    
    def is_emergency_stop(self) -> bool:
        """Check if emergency stop is activated."""
        return self.credentials.get('emergency_stop', False)
    
    def get_config(self, section: str = None) -> Dict[str, Any]:
        """
        Get configuration section or entire config.
        
        Args:
            section: Configuration section name (optional)
            
        Returns:
            Configuration dictionary
        """
        if section:
            return self.config.get(section, {})
        return self.config.copy()
    
    def update_config(self, section: str, key: str, value: Any):
        """
        Update configuration value.
        
        Args:
            section: Configuration section
            key: Configuration key
            value: New value
        """
        if section not in self.config:
            self.config[section] = {}
        
        self.config[section][key] = value
        self.logger.info(f"Updated config: {section}.{key} = {value}")
    
    def save_config(self, config_file: str = None):
        """
        Save current configuration to file.
        
        Args:
            config_file: Output file path (optional)
        """
        if not config_file:
            config_file = self.config_dir / "settings.yaml"
        
        with open(config_file, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, indent=2)
        
        self.logger.info(f"Configuration saved to {config_file}")
