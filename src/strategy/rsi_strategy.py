"""
Estrategia de reversión a la media usando RSI y Bollinger Bands.
"""
from typing import Dict, Literal

Decision = Literal["YES", "NO", "SKIP"]

class RSIStrategy:
    """
    Estrategia de reversión a la media mejorada.
    Combina RSI con Bollinger Bands para señales más robustas.
    """

    def __init__(
        self,
        rsi_low: float = 30.0,
        rsi_high: float = 70.0,
        min_bb_width: float = 0.01,    # Mínimo ancho de BB (1%)
        require_wide_bands: bool = True  # Requiere que las BB estén anchas
    ):
        self.rsi_low = rsi_low
        rsi_high = rsi_high
        self.min_bb_width = min_bb_width
        self.require_wide_bands = require_wide_bands

    def decide(self, features: Dict) -> Decision:
        """
        Toma decisión basada en RSI y Bollinger Bands.

        Lógica:
        - RSI < 30 + precio cerca de lower band → YES (oversold + bounce)
        - RSI > 70 + precio cerca de upper band → NO (overbought + pullback)
        - Si las BB están muy estrechas → SKIP (sin volatilidad)
        """
        rsi = features.get("rsi_14", 50)
        bb_width = features.get("bb_width", 0)
        bb_upper = features.get("bb_upper", 0)
        bb_lower = features.get("bb_lower", 0)
        close = features.get("close", 0)

        # Verificar que tengamos suficientes datos
        if rsi is None or bb_width is None:
            return "SKIP"

        # Si requerimos BB anchas y están muy estrechas → SKIP
        if self.require_wide_bands and bb_width < self.min_bb_width:
            return "SKIP"

        # Oversold: RSI bajo + precio cerca de lower band
        if rsi < self.rsi_low:
            if close < (bb_upper + bb_lower) / 2:  # En mitad inferior del rango
                return "YES"
            return "SKIP"

        # Overbought: RSI alto + precio cerca de upper band
        if rsi > self.rsi_high:
            if close > (bb_upper + bb_lower) / 2:  # En mitad superior del rango
                return "NO"
            return "SKIP"

        return "SKIP"