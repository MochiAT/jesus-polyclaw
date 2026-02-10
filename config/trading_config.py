"""
Configuración centralizada del sistema de trading.
Este archivo centraliza todos los parámetros para facilitar la optimización y ajustes.
"""
from dataclasses import dataclass
from typing import List, Dict
from enum import Enum

class AssetType(Enum):
    BTC = "BTC"
    ETH = "ETH"
    XRP = "XRP"

class Timeframe(Enum):
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"

@dataclass
class TradingConfig:
    """Configuración general del sistema de trading"""
    # Activos y Timeframes
    assets: List[str] = None
    timeframes: List[str] = None

    # Configuración de Oracle
    exchange: str = "kraken"
    enable_rate_limit: bool = True
    timeout_ms: int = 25000

    # Gestión de Riesgo
    max_position_size: float = 0.10  # 10% del balance máximo por posición
    stop_loss_pct: float = 0.05  # 5% stop loss
    take_profit_pct: float = 0.10  # 10% take profit
    max_drawdown_pct: float = 0.20  # 20% max drawdown
    daily_loss_limit: float = 0.03  # 3% pérdida diaria máxima

    # Configuración de Backtesting
    start_balance: float = 1000.0
    entry_price: float = 0.5
    position_size: float = 10.0
    min_trades_for_validation: int = 20

    # Configuración de Market Selection
    market_prefix: str = "updown"
    min_market_liquidity: float = 1000.0  # Mínimo $1000 en el mercado
    max_spread_pct: float = 0.05  # Máximo 5% de spread

    # Configuración de Logging
    log_level: str = "INFO"
    log_file: str = "polyclaw-jesus.log"
    enable_structured_logging: bool = True

    # Configuración de Monitoreo
    alert_on_drawdown: bool = True
    alert_on_trades: bool = False
    dashboard_enabled: bool = True

    def __post_init__(self):
        if self.assets is None:
            self.assets = ["btc", "eth", "xrp"]
        if self.timeframes is None:
            self.timeframes = ["15m", "30m", "1h"]

    def get_asset_mapping(self) -> Dict[str, str]:
        """Mapeo de activos a símbolos de exchange"""
        return {
            "btc": "BTC/USD",
            "eth": "ETH/USD",
            "xrp": "XRP/USD"
        }

# Instancia global de configuración
CONFIG = TradingConfig()