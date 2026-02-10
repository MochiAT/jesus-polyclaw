"""
Tests para DataValidator.
"""
import pytest
import pandas as pd
import numpy as np
from src.data.data_validator import DataValidator


class TestDataValidator:
    """Test suite para DataValidator"""

    def setup_method(self):
        """Setup para cada test"""
        self.validator = DataValidator()

    def test_valid_ohlcv_data(self):
        """Test de datos OHLCV válidos"""
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='15min'),
            'open': np.linspace(45000, 46000, 100),
            'high': np.linspace(45100, 46100, 100),
            'low': np.linspace(44900, 45900, 100),
            'close': np.linspace(45050, 46050, 100),
            'volume': np.random.uniform(100, 1000, 100)
        })

        is_valid, report = self.validator.validate_ohlcv(df)
        assert is_valid is True
        assert report['status'] == 'valid'

    def test_missing_columns(self):
        """Test de datos con columnas faltantes"""
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='15min'),
            'open': np.linspace(45000, 46000, 100),
            # Faltan high, low, close, volume
        })

        is_valid, report = self.validator.validate_ohlcv(df)
        assert is_valid is False
        assert 'Missing columns' in report['reason']

    def test_null_values(self):
        """Test de datos con valores nulos"""
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='15min'),
            'open': np.linspace(45000, 46000, 100),
            'high': np.linspace(45100, 46100, 100),
            'low': np.linspace(44900, 45900, 100),
            'close': np.linspace(45050, 46050, 100),
            'volume': np.random.uniform(100, 1000, 100)
        })
        df.loc[50, 'close'] = None  # Introducir NaN

        is_valid, report = self.validator.validate_ohlcv(df)
        assert is_valid is False
        assert 'Null values' in report['reason']

    def test_ohlc_violations(self):
        """Test de violaciones en relaciones OHLC"""
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='15min'),
            'open': np.linspace(45000, 46000, 100),
            'high': np.linspace(44900, 45900, 100),  # High menor que open
            'low': np.linspace(45100, 46100, 100),    # Low mayor que open
            'close': np.linspace(45050, 46050, 100),
            'volume': np.random.uniform(100, 1000, 100)
        })

        is_valid, report = self.validator.validate_ohlcv(df)
        assert is_valid is False
        assert 'OHLC relationship violations' in report['reason']

    def test_clean_data_forward_fill(self):
        """Test de limpieza de datos con forward fill"""
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='15min'),
            'open': np.linspace(45000, 46000, 100),
            'high': np.linspace(45100, 46100, 100),
            'low': np.linspace(44900, 45900, 100),
            'close': np.linspace(45050, 46050, 100),
            'volume': np.random.uniform(100, 1000, 100)
        })
        df.loc[50:52, 'close'] = None  # Introducir NaN

        cleaned_df = self.validator.clean_data(df, method='forward_fill')
        assert cleaned_df.isnull().sum().sum() == 0

    def test_clean_data_drop(self):
        """Test de limpieza de datos con drop"""
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='15min'),
            'open': np.linspace(45000, 46000, 100),
            'high': np.linspace(45100, 46100, 100),
            'low': np.linspace(44900, 45900, 100),
            'close': np.linspace(45050, 46050, 100),
            'volume': np.random.uniform(100, 1000, 100)
        })
        df.loc[50:52, 'close'] = None  # Introducir NaN

        cleaned_df = self.validator.clean_data(df, method='drop')
        assert cleaned_df.isnull().sum().sum() == 0
        assert len(cleaned_df) == 97  # 100 - 3 rows with NaN