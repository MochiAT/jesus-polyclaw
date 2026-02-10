"""
Validación robusta de datos de mercado.
Detecta anomalías, valores faltantes y outliers.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy import stats

class DataValidator:
    """
    Validador de datos de mercado para asegurar calidad antes de análisis.
    """

    def __init__(self, z_score_threshold: float = 3.0, price_change_threshold: float = 0.50):
        self.z_score_threshold = z_score_threshold
        self.price_change_threshold = price_change_threshold
        self.validation_results = []

    def validate_ohlcv(self, df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
        """
        Valida datos OHLCV de velas.

        Returns:
            (is_valid, validation_report)
        """
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

        # 1. Verificar columnas requeridas
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            return False, {
                "status": "invalid",
                "reason": f"Missing columns: {missing_cols}",
                "suggestion": "Ensure all OHLCV columns are present"
            }

        # 2. Verificar valores faltantes
        null_counts = df[required_columns].isnull().sum()
        if null_counts.any():
            return False, {
                "status": "invalid",
                "reason": f"Null values found: {null_counts[null_counts > 0].to_dict()}",
                "suggestion": "Fill or drop null values"
            }

        # 3. Validar relaciones OHLC (high >= low, high >= open/close, low <= open/close)
        violations = self._check_ohlc_relationships(df)
        if violations > 0:
            return False, {
                "status": "invalid",
                "reason": f"OHLC relationship violations: {violations}",
                "suggestion": "Correct OHLC data or discard affected candles"
            }

        # 4. Detectar outliers en precio
        outliers = self._detect_price_outliers(df)
        if len(outliers) > 0:
            return False, {
                "status": "warning",
                "reason": f"Price outliers detected at indices: {outliers}",
                "suggestion": "Review outliers and consider capping or removal",
                "outlier_indices": outliers.tolist()
            }

        # 5. Verificar cambios extremos de precio
        extreme_changes = self._detect_extreme_price_changes(df)
        if len(extreme_changes) > 0:
            return False, {
                "status": "warning",
                "reason": f"Extreme price changes detected at indices: {extreme_changes}",
                "suggestion": "Review extreme changes",
                "extreme_change_indices": extreme_changes.tolist()
            }

        # 6. Verificar volumen no negativo
        if (df['volume'] < 0).any():
            return False, {
                "status": "invalid",
                "reason": "Negative volume values found",
                "suggestion": "Correct or remove negative volumes"
            }

        # 7. Verificar timestamps ordenados
        if not df['timestamp'].is_monotonic_increasing:
            return False, {
                "status": "invalid",
                "reason": "Timestamps not monotonically increasing",
                "suggestion": "Sort data by timestamp"
            }

        return True, {
            "status": "valid",
            "rows": len(df),
            "time_range": {
                "start": str(df['timestamp'].min()),
                "end": str(df['timestamp'].max())
            }
        }

    def _check_ohlc_relationships(self, df: pd.DataFrame) -> int:
        """
        Verifica que high >= low, high >= open/close, low <= open/close.
        Retorna el número de violaciones.
        """
        violations = 0
        violations += (df['high'] < df['low']).sum()
        violations += (df['high'] < df['open']).sum()
        violations += (df['high'] < df['close']).sum()
        violations += (df['low'] > df['open']).sum()
        violations += (df['low'] > df['close']).sum()

        return int(violations)

    def _detect_price_outliers(self, df: pd.DataFrame, column: str = 'close') -> np.ndarray:
        """
        Detecta outliers usando Z-score.
        Retorna los índices de outliers.
        """
        z_scores = np.abs(stats.zscore(df[column]))
        outlier_indices = np.where(z_scores > self.z_score_threshold)[0]
        return outlier_indices

    def _detect_extreme_price_changes(self, df: pd.DataFrame, column: str = 'close') -> np.ndarray:
        """
        Detecta cambios extremos de precio (gaps) entre velas.
        Retorna los índices donde ocurren cambios extremos.
        """
        price_changes = df[column].pct_change().abs()
        extreme_indices = np.where(price_changes > self.price_change_threshold)[0]
        return extreme_indices

    def validate_features(self, df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
        """
        Valida features calculadas.
        """
        # Verificar valores NaN/Inf
        nan_cols = df.columns[df.isnull().any()].tolist()
        if nan_cols:
            return False, {
                "status": "invalid",
                "reason": f"NaN values in columns: {nan_cols}",
                "suggestion": "Fill NaN values or check feature calculation"
            }

        # Verificar infinitos
        inf_cols = []
        for col in df.columns:
            if np.isinf(df[col]).any():
                inf_cols.append(col)

        if inf_cols:
            return False, {
                "status": "invalid",
                "reason": f"Infinite values in columns: {inf_cols}",
                "suggestion": "Check for division by zero in feature calculation"
            }

        return True, {
            "status": "valid",
            "features_count": len(df.columns),
            "rows": len(df)
        }

    def clean_data(self, df: pd.DataFrame, method: str = "forward_fill") -> pd.DataFrame:
        """
        Limpia datos según el método especificado.

        Args:
            df: DataFrame a limpiar
            method: 'forward_fill', 'drop', 'interpolate'
        """
        df_clean = df.copy()

        if method == "forward_fill":
            df_clean = df_clean.fillna(method='ffill').fillna(method='bfill')
        elif method == "drop":
            df_clean = df_clean.dropna()
        elif method == "interpolate":
            df_clean = df_clean.interpolate(method='linear')
        else:
            raise ValueError(f"Unknown cleaning method: {method}")

        return df_clean

    def get_validation_summary(self) -> List[Dict[str, Any]]:
        """Retorna resumen de validaciones realizadas"""
        return self.validation_results