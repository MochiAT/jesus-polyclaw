"""
Sistema completo de gestión de riesgo.
Controla exposición, drawdown, y límites de pérdida.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum
from datetime import datetime
import numpy as np

class RiskLevel(Enum):
    """Niveles de riesgo"""
    GREEN = "green"    # Riesgo bajo, operación normal
    YELLOW = "yellow"  # Riesgo medio, precaución
    RED = "red"        # Riesgo alto, parar trading

@dataclass
class Position:
    """Representa una posición abierta"""
    market_id: str
    side: str  # "YES" o "NO"
    entry_price: float
    size: float
    entry_time: datetime
    stop_loss: float
    take_profit: float

@dataclass
class RiskMetrics:
    """Métricas de riesgo actuales"""
    current_balance: float
    equity_peak: float
    current_drawdown: float
    max_drawdown: float
    daily_pnl: float
    open_positions_value: float
    total_exposure: float

@dataclass
class RiskConfig:
    """Configuración de parámetros de riesgo"""
    max_position_size_pct: float = 0.10  # 10% del balance por posición
    max_total_exposure_pct: float = 0.30  # 30% del balance total expuesto
    stop_loss_pct: float = 0.05  # 5% stop loss
    take_profit_pct: float = 0.10  # 10% take profit
    max_drawdown_pct: float = 0.20  # 20% max drawdown global
    daily_loss_limit_pct: float = 0.03  # 3% pérdida diaria máxima
    max_open_positions: int = 3
    min_risk_reward_ratio: float = 2.0  # Mínimo ratio riesgo/recompensa

class RiskManager:
    """
    Gestor de riesgo central del sistema.
    Controla tamaño de posición, stop-loss, y exposición.
    """

    def __init__(self, config: RiskConfig = None, initial_balance: float = 1000.0):
        self.config = config or RiskConfig()
        self.balance = initial_balance
        self.equity_peak = initial_balance
        self.max_drawdown = 0.0
        self.daily_pnl = 0.0
        self.daily_start_balance = initial_balance
        self.open_positions: Dict[str, Position] = {}
        self.risk_level = RiskLevel.GREEN
        self.blocked_trades: List[Dict] = []

    def calculate_position_size(self, price: float, risk_amount: float = None) -> float:
        """
        Calcula tamaño de posición basado en riesgo.

        Args:
            price: Precio de entrada
            risk_amount: Monto de riesgo en $ (opcional, usa config si no se especifica)

        Returns:
            Tamaño de posición (número de contratos/shares)
        """
        if risk_amount is None:
            risk_amount = self.balance * self.config.stop_loss_pct

        # Calcular tamaño de posición
        position_size = risk_amount / (price * self.config.stop_loss_pct)

        # Limitar por máximo permitido
        max_size_by_balance = (self.balance * self.config.max_position_size_pct) / price
        position_size = min(position_size, max_size_by_balance)

        return round(position_size, 4)

    def validate_trade(self, market_id: str, side: str, price: float, size: float,
                      confidence: float = 0.5) -> Tuple[bool, Optional[str]]:
        """
        Valida si un trade debe permitirse según reglas de riesgo.

        Returns:
            (is_allowed, reason)
        """
        # 1. Verificar nivel de riesgo
        if self.risk_level == RiskLevel.RED:
            self.blocked_trades.append({
                "market_id": market_id,
                "reason": "RED risk level - trading halted",
                "timestamp": datetime.utcnow()
            })
            return False, "Trading halted due to excessive risk"

        # 2. Verificar número máximo de posiciones
        if len(self.open_positions) >= self.config.max_open_positions:
            return False, f"Maximum open positions reached ({self.config.max_open_positions})"

        # 3. Verificar tamaño de posición
        position_value = price * size
        max_position_value = self.balance * self.config.max_position_size_pct
        if position_value > max_position_value:
            return False, f"Position too large: ${position_value:.2f} > ${max_position_value:.2f}"

        # 4. Verificar exposición total
        total_exposure = sum(pos.entry_price * pos.size for pos in self.open_positions.values())
        new_exposure = total_exposure + position_value
        max_exposure = self.balance * self.config.max_total_exposure_pct
        if new_exposure > max_exposure:
            return False, f"Total exposure too high: ${new_exposure:.2f} > ${max_exposure:.2f}"

        # 5. Verificar límite de pérdida diaria
        if self.daily_pnl < -(self.balance * self.config.daily_loss_limit_pct):
            self.risk_level = RiskLevel.RED
            return False, f"Daily loss limit reached: {self.daily_pnl:.2f}"

        # 6. Verificar ratio riesgo/recompensa
        if confidence < 0.5:
            return False, f"Confidence too low: {confidence:.2f}"

        return True, None

    def open_position(self, market_id: str, side: str, price: float, size: float) -> Position:
        """
        Abre una posición y configura stop-loss/take-profit.
        """
        stop_loss = price * (1 - self.config.stop_loss_pct) if side == "YES" else price * (1 + self.config.stop_loss_pct)
        take_profit = price * (1 + self.config.take_profit_pct) if side == "YES" else price * (1 - self.config.take_profit_pct)

        position = Position(
            market_id=market_id,
            side=side,
            entry_price=price,
            size=size,
            entry_time=datetime.utcnow(),
            stop_loss=stop_loss,
            take_profit=take_profit
        )

        self.open_positions[market_id] = position
        self._update_risk_level()

        return position

    def check_position_exit(self, market_id: str, current_price: float) -> Optional[str]:
        """
        Verifica si una posición debe cerrarse por stop-loss o take-profit.

        Returns:
            'stop_loss', 'take_profit', o None
        """
        if market_id not in self.open_positions:
            return None

        position = self.open_positions[market_id]

        if position.side == "YES":
            if current_price <= position.stop_loss:
                return "stop_loss"
            if current_price >= position.take_profit:
                return "take_profit"
        else:  # NO
            if current_price >= position.stop_loss:
                return "stop_loss"
            if current_price <= position.take_profit:
                return "take_profit"

        return None

    def close_position(self, market_id: str, exit_price: float, exit_reason: str = "manual") -> float:
        """
        Cierra una posición y actualiza métricas.

        Returns:
            PnL de la operación
        """
        if market_id not in self.open_positions:
            return 0.0

        position = self.open_positions[market_id]
        exit_value = exit_price * position.size
        entry_value = position.entry_price * position.size

        if position.side == "YES":
            pnl = exit_value - entry_value
        else:
            pnl = entry_value - exit_value

        # Actualizar balance y métricas
        self.balance += pnl
        self.daily_pnl += pnl

        # Actualizar peak y drawdown
        if self.balance > self.equity_peak:
            self.equity_peak = self.balance
            self.max_drawdown = 0.0
        else:
            self.max_drawdown = max(self.max_drawdown, (self.equity_peak - self.balance) / self.equity_peak)

        # Remover posición
        del self.open_positions[market_id]
        self._update_risk_level()

        return pnl

    def get_risk_metrics(self) -> RiskMetrics:
        """
        Retorna métricas actuales de riesgo.
        """
        current_drawdown = (self.equity_peak - self.balance) / self.equity_peak if self.equity_peak > 0 else 0
        open_positions_value = sum(pos.entry_price * pos.size for pos in self.open_positions.values())
        total_exposure = open_positions_value

        return RiskMetrics(
            current_balance=self.balance,
            equity_peak=self.equity_peak,
            current_drawdown=current_drawdown,
            max_drawdown=self.max_drawdown,
            daily_pnl=self.daily_pnl,
            open_positions_value=open_positions_value,
            total_exposure=total_exposure
        )

    def _update_risk_level(self):
        """Actualiza el nivel de riesgo basado en métricas actuales"""
        metrics = self.get_risk_metrics()

        if metrics.current_drawdown >= self.config.max_drawdown_pct:
            self.risk_level = RiskLevel.RED
        elif metrics.current_drawdown >= self.config.max_drawdown_pct * 0.5:
            self.risk_level = RiskLevel.YELLOW
        else:
            self.risk_level = RiskLevel.GREEN

    def reset_daily(self):
        """Resetea métricas diarias"""
        self.daily_pnl = 0.0
        self.daily_start_balance = self.balance

    def get_blocked_trades_summary(self) -> List[Dict]:
        """Retorna resumen de trades bloqueados"""
        return self.blocked_trades