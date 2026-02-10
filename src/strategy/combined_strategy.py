"""
Estrategia combinada que integra múltiples indicadores.
"""
from typing import Dict, Literal

Decision = Literal["YES", "NO", "SKIP"]

class CombinedStrategy:
    """
    Estrategia combinada que usa RSI, MACD, Momentum y Bollinger Bands.
    Requiere consenso entre múltiples indicadores.
    """

    def __init__(
        self,
        rsi_low: float = 30.0,
        rsi_high: float = 70.0,
        min_momentum: float = 0.001,  # 0.1%
        require_macd_confirmation: bool = True
    ):
        self.rsi_low = rsi_low
        self.rsi_high = rsi_high
        self.min_momentum = min_momentum
        self.require_macd_confirmation = require_macd_confirmation

    def decide(self, features: Dict) -> Decision:
        """
        Toma decisión basada en consenso de múltiples indicadores.

        Lógica:
        - Para YES: RSI bajo + Momentum positivo + (opcional) MACD positivo
        - Para NO: RSI alto + Momentum negativo + (opcional) MACD negativo
        """
        rsi = features.get("rsi_14", 50)
        momentum = features.get("momentum_3", 0)
        macd = features.get("macd", 0)
        macd_diff = features.get("macd_diff", 0)

        # Verificar que tengamos datos suficientes
        if any(v is None for v in [rsi, momentum, macd, macd_diff]):
            return "SKIP"

        # Signals para YES (compra/long)
        yes_signals = 0

        # RSI oversold
        if rsi < self.rsi_low:
            yes_signals += 1

        # Momentum positivo
        if momentum > self.min_momentum:
            yes_signals += 1

        # MACD confirmación (opcional)
        if self.require_macd_confirmation:
            if macd > 0 and macd_diff > 0:
                yes_signals += 1
        else:
            yes_signals += 1  # Si no se requiere, contar como positivo

        # Signals para NO (venta/short)
        no_signals = 0

        # RSI overbought
        if rsi > self.rsi_high:
            no_signals += 1

        # Momentum negativo
        if momentum < -self.min_momentum:
            no_signals += 1

        # MACD confirmación (opcional)
        if self.require_macd_confirmation:
            if macd < 0 and macd_diff < 0:
                no_signals += 1
        else:
            no_signals += 1  # Si no se requiere, contar como positivo

        # Requirimos todos los signals para tomar decisión
        if yes_signals == 3:
            return "YES"
        if no_signals == 3:
            return "NO"

        return "SKIP"

class AdaptiveRSIStrategy:
    """
    Estrategia RSI adaptativa que ajusta thresholds según volatilidad.
    """

    def __init__(
        self,
        base_rsi_low: float = 30.0,
        base_rsi_high: float = 70.0,
        atr_adjustment: bool = True
    ):
        self.base_rsi_low = base_rsi_low
        self.base_rsi_high = base_rsi_high
        self.atr_adjustment = atr_adjustment

    def decide(self, features: Dict) -> Decision:
        """
        Ajusta thresholds de RSI según ATR (volatilidad).

        En alta volatilidad → thresholds más extremos (más conservador)
        En baja volatilidad → thresholds más moderados
        """
        rsi = features.get("rsi_14", 50)
        atr = features.get("atr_14", 0)
        close = features.get("close", 1)

        if rsi is None or atr is None:
            return "SKIP"

        # Calcular volatilidad relativa
        relative_volatility = atr / close if close > 0 else 0

        # Ajustar thresholds según volatilidad
        if self.atr_adjustment:
            # Más volatilidad → thresholds más extremos
            vol_multiplier = 1 + relative_volatility * 10
            adjusted_low = max(20, min(40, self.base_rsi_low / vol_multiplier))
            adjusted_high = min(80, max(60, self.base_rsi_high * vol_multiplier))
        else:
            adjusted_low = self.base_rsi_low
            adjusted_high = self.base_rsi_high

        # Decisión con thresholds ajustados
        if rsi < adjusted_low:
            return "YES"
        if rsi > adjusted_high:
            return "NO"

        return "SKIP"