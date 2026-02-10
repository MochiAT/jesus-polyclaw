"""
Cálculo de features técnicas para análisis de mercado.
Reutilizado de polyclaw con mejoras de manejo de NaN.
"""
import pandas as pd
import numpy as np
import ta
from typing import Optional
from src.utils.logger import logger

def compute_features(df: pd.DataFrame, drop_na: bool = True) -> pd.DataFrame:
    """
    Calcula features técnicas sobre datos OHLCV.

    Espera OHLCV con columnas:
    ['timestamp','open','high','low','close','volume']

    Devuelve el mismo DF con features añadidas.

    Args:
        df: DataFrame con datos OHLCV
        drop_na: Si True, elimina filas con NaN

    Returns:
        DataFrame con features añadidas
    """
    out = df.copy()

    try:
        # RSI
        out["rsi_14"] = ta.momentum.RSIIndicator(
            close=out["close"], window=14
        ).rsi()

        # MACD
        macd = ta.trend.MACD(close=out["close"])
        out["macd"] = macd.macd()
        out["macd_signal"] = macd.macd_signal()
        out["macd_diff"] = macd.macd_diff()

        # Momentum simple
        out["momentum_3"] = out["close"].pct_change(3)
        out["momentum_6"] = out["close"].pct_change(6)

        # Volatilidad (ATR)
        out["atr_14"] = ta.volatility.AverageTrueRange(
            high=out["high"],
            low=out["low"],
            close=out["close"],
            window=14
        ).average_true_range()

        # Bollinger Bands (nuevas features)
        bb = ta.volatility.BollingerBands(
            close=out["close"],
            window=20,
            window_dev=2
        )
        out["bb_upper"] = bb.bollinger_hband()
        out["bb_lower"] = bb.bollinger_lband()
        out["bb_middle"] = bb.bollinger_mavg()
        out["bb_width"] = (out["bb_upper"] - out["bb_lower"]) / out["bb_middle"]

        # Volume indicators (nuevas features)
        out["volume_sma_20"] = out["volume"].rolling(window=20).mean()
        out["volume_ratio"] = out["volume"] / out["volume_sma_20"]

        # Price position relative to range (nueva feature)
        out["range_position"] = (out["close"] - out["low"]) / (out["high"] - out["low"])

        logger.log_error(
            error_type="features_success",
            error_msg=f"Successfully computed {len(out.columns) - len(df.columns)} features",
            context={"rows": len(out), "original_cols": len(df.columns), "new_cols": len(out.columns)}
        )

        if drop_na:
            nan_count = out.isnull().sum().sum()
            if nan_count > 0:
                logger.log_error(
                    error_type="features_dropping_nan",
                    error_msg=f"Dropping {nan_count} NaN values from features",
                    context={"nan_count": nan_count}
                )
            out = out.dropna().reset_index(drop=True)

        return out

    except Exception as e:
        logger.log_error(
            error_type="features_error",
            error_msg=f"Error computing features: {str(e)}",
            context={"error": str(e), "shape": df.shape}
        )
        raise

def latest_features(df: pd.DataFrame) -> dict:
    """
    Devuelve solo las features más recientes (última vela cerrada).
    """
    row = df.iloc[-1]
    return {
        "close": float(row["close"]),
        "rsi_14": float(row["rsi_14"]),
        "macd": float(row["macd"]),
        "macd_signal": float(row["macd_signal"]),
        "macd_diff": float(row["macd_diff"]),
        "momentum_3": float(row["momentum_3"]),
        "momentum_6": float(row["momentum_6"]),
        "atr_14": float(row["atr_14"]),
        "bb_upper": float(row["bb_upper"]),
        "bb_lower": float(row["bb_lower"]),
        "bb_width": float(row["bb_width"]),
        "volume_ratio": float(row["volume_ratio"]),
        "range_position": float(row["range_position"]),
    }

def compute_feature_importance(df: pd.DataFrame) -> dict:
    """
    Calcula importancia relativa de features basado en correlación con retornos futuros.

    Returns:
        Dict con importancia de cada feature
    """
    features_df = compute_features(df)

    # Calcular retornos futuros (1 candle ahead)
    features_df["future_return"] = features_df["close"].pct_change(-1)

    feature_cols = [
        "rsi_14", "macd", "macd_diff", "momentum_3", "momentum_6",
        "atr_14", "bb_width", "volume_ratio", "range_position"
    ]

    importance = {}
    for col in feature_cols:
        if col in features_df.columns:
            corr = features_df[col].corr(features_df["future_return"])
            importance[col] = abs(corr) if not np.isnan(corr) else 0.0

    return importance

if __name__ == "__main__":
    # Test de features
    import numpy as np

    # Generar datos de prueba
    np.random.seed(42)
    n = 200
    base_price = 45000
    prices = base_price + np.cumsum(np.random.normal(0, 100, n))
    df = pd.DataFrame({
        "timestamp": pd.date_range(start="2024-01-01", periods=n, freq="15min"),
        "open": prices[:-1] if n > 1 else prices,
        "high": prices * (1 + np.abs(np.random.normal(0, 0.01, n-1))),
        "low": prices * (1 - np.abs(np.random.normal(0, 0.01, n-1))),
        "close": prices,
        "volume": np.random.uniform(100, 1000, n)
    })

    df = df[:-1]  # Ajustar para que coincidan las dimensiones

    print("Original DataFrame:")
    print(df.head())
    print()

    df_with_features = compute_features(df)
    print("DataFrame with features:")
    print(df_with_features.head())
    print()

    print("Latest features:")
    latest = latest_features(df_with_features)
    for k, v in latest.items():
        print(f"  {k}: {v:.4f}")