"""
Tests para estrategias de trading.
"""
import pytest
from src.strategy.baseline_strategy import BaselineStrategy
from src.strategy.rsi_strategy import RSIStrategy
from src.strategy.combined_strategy import CombinedStrategy, AdaptiveRSIStrategy


class TestBaselineStrategy:
    """Test suite para BaselineStrategy"""

    def setup_method(self):
        """Setup para cada test"""
        self.strategy = BaselineStrategy()

    def test_momentum_positive_above_threshold(self):
        """Test con momentum positivo sobre threshold"""
        features = {
            'momentum_3': 0.002,  # 0.2% > 0.1%
            'range_position': 0.8    # En parte superior
        }
        decision = self.strategy.decide(features)
        assert decision == "YES"

    def test_momentum_negative_below_threshold(self):
        """Test con momentum negativo bajo threshold"""
        features = {
            'momentum_3': -0.002,  # -0.2% < -0.1%
            'range_position': 0.2   # En parte inferior
        }
        decision = self.strategy.decide(features)
        assert decision == "NO"

    def test_momentum_below_threshold_skip(self):
        """Test con momentum bajo threshold"""
        features = {
            'momentum_3': 0.0005,  # 0.05% < 0.1%
            'range_position': 0.8
        }
        decision = self.strategy.decide(features)
        assert decision == "SKIP"

    def test_momentum_positive_low_range_position_skip(self):
        """Test con momentum positivo pero en parte inferior del rango"""
        features = {
            'momentum_3': 0.002,  # 0.2% > 0.1%
            'range_position': 0.1   # En parte inferior
        }
        decision = self.strategy.decide(features)
        assert decision == "SKIP"


class TestRSIStrategy:
    """Test suite para RSIStrategy"""

    def setup_method(self):
        """Setup para cada test"""
        self.strategy = RSIStrategy()

    def test_rsi_oversold(self):
        """Test con RSI en oversold"""
        features = {
            'rsi_14': 25.0,
            'close': 45000,
            'bb_upper': 46000,
            'bb_lower': 44000
        }
        decision = self.strategy.decide(features)
        assert decision == "YES"

    def test_rsi_overbought(self):
        """Test con RSI en overbought"""
        features = {
            'rsi_14': 75.0,
            'close': 46000,
            'bb_upper': 46000,
            'bb_lower': 44000
        }
        decision = self.strategy.decide(features)
        assert decision == "NO"

    def test_rsi_neutral(self):
        """Test con RSI en zona neutra"""
        features = {
            'rsi_14': 50.0,
            'bb_width': 0.05,
            'close': 45000,
            'bb_upper': 46000,
            'bb_lower': 44000
        }
        decision = self.strategy.decide(features)
        assert decision == "SKIP"


class TestCombinedStrategy:
    """Test suite para CombinedStrategy"""

    def setup_method(self):
        """Setup para cada test"""
        self.strategy = CombinedStrategy()

    def test_strong_buy_signals(self):
        """Test con señales fuertes de compra"""
        features = {
            'rsi_14': 25.0,      # Oversold
            'momentum_3': 0.002, # Momentum positivo
            'macd': 100.0,       # MACD positivo
            'macd_diff': 50.0    # MACD diff positivo
        }
        decision = self.strategy.decide(features)
        assert decision == "YES"

    def test_strong_sell_signals(self):
        """Test con señales fuertes de venta"""
        features = {
            'rsi_14': 75.0,       # Overbought
            'momentum_3': -0.002, # Momentum negativo
            'macd': -100.0,       # MACD negativo
            'macd_diff': -50.0    # MACD diff negativo
        }
        decision = self.strategy.decide(features)
        assert decision == "NO"

    def test_mixed_signals_skip(self):
        """Test con señales mixtas"""
        features = {
            'rsi_14': 25.0,      # Oversold → YES signal
            'momentum_3': -0.002, # Momentum negativo → NO signal
            'macd': 100.0,
            'macd_diff': 50.0
        }
        decision = self.strategy.decide(features)
        assert decision == "SKIP"


class TestAdaptiveRSIStrategy:
    """Test suite para AdaptiveRSIStrategy"""

    def setup_method(self):
        """Setup para cada test"""
        self.strategy = AdaptiveRSIStrategy()

    def test_low_volatility_oversold(self):
        """Test con baja volatilidad y RSI oversold"""
        features = {
            'rsi_14': 28.0,      # Ligeramente below 30
            'atr_14': 100.0,     # ATR bajo
            'close': 45000.0
        }
        decision = self.strategy.decide(features)
        # En baja volatilidad, thresholds se relajan → 28 puede ser suficiente
        assert decision in ["YES", "SKIP"]

    def test_high_volatility_neutral(self):
        """Test con alta volatilidad y RSI en zona neutra"""
        features = {
            'rsi_14': 35.0,      # En zona neutra
            'atr_14': 2000.0,    # ATR alto
            'close': 45000.0
        }
        decision = self.strategy.decide(features)
        # En alta volatilidad, thresholds se vuelven más estrictos
        assert decision == "SKIP"

    def test_oversold_high_volatility(self):
        """Test con alta volatilidad y RSI muy oversold"""
        features = {
            'rsi_14': 20.0,      # Muy oversold
            'atr_14': 2000.0,    # ATR alto
            'close': 45000.0
        }
        decision = self.strategy.decide(features)
        # Incluso con alta volatilidad, RSI muy oversold debe dar señal
        assert decision == "YES"