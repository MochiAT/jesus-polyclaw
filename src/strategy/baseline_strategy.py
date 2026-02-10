"""
Estrategia baseline mejorada basada en momentum y dirección.
"""
from typing import Dict, Literal

Decision = Literal["YES", "NO", "SKIP"]

class BaselineStrategy:
    """
    Estrategia baseline mejorada.
    Combina momentum con posición en rango de precios.
    """

    def __init__(
        self,
        momentum_threshold: float = 0.001,  # 0.1% threshold
        min_range_position: float = 0.3,     # Mínimo posición en rango
        max_range_position: float = 0.7       # Máximo posición en rango
    ):
        self.momentum_threshold = momentum_threshold
        self.min_range_position = min_range_position
        self.max_range_position = max_range_position

    def decide(self, features: Dict) -> Decision:
        """
        Toma decisión basada en momentum y posición en rango.

        Lógica:
        - Si momentum positivo y precio en parte superior del rango → YES
        - Si momentum negativo y precio en parte inferior del rango → NO
        - Si momentum pequeño → SKIP
        """
        momentum = features.get("momentum_3", 0)
        range_position = features.get("range_position", 0.5)

        # Verificar que tengamos suficientes datos
        if momentum is None or range_position is None:
            return "SKIP"

        # Verificar thresholds
        abs_momentum = abs(momentum)
        if abs_momentum < self.momentum_threshold:
            return "SKIP"

        # Momentum positivo
        if momentum > 0:
            if range_position > self.min_range_position:
                return "YES"
            return "SKIP"

        # Momentum negativo
        if momentum < 0:
            if range_position < self.max_range_position:
                return "NO"
            return "SKIP"

        return "SKIP"