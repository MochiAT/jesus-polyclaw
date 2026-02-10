"""
Oracle de precios para datos de criptomonedas.
Reutilizado de polyclaw con mejoras de manejo de errores.
"""
import ccxt
import pandas as pd
from typing import Optional
from src.utils.logger import logger

class OraclePriceFeed:
    """
    Feed de precios OHLCV desde exchanges centralizados.
    Mejorado con retry y logging detallado.
    """

    def __init__(self, exchange: str = "kraken", enable_rate_limit: bool = True):
        self.exchange_name = exchange.lower()
        self.enable_rate_limit = enable_rate_limit

        if self.exchange_name == "kraken":
            self.exchange = ccxt.kraken({"enableRateLimit": enable_rate_limit})
            self.default_symbol = "BTC/USD"
        elif self.exchange_name == "coinbase":
            self.exchange = ccxt.coinbase({"enableRateLimit": enable_rate_limit})
            self.default_symbol = "BTC/USD"
        elif self.exchange_name == "binance":
            self.exchange = ccxt.binance({"enableRateLimit": enable_rate_limit})
            self.default_symbol = "BTC/USDT"
        else:
            raise ValueError(f"Unsupported exchange: {exchange}")

        logger.log_error(
            error_type="oracle_init",
            error_msg=f"Oracle initialized with {self.exchange_name}",
            context={"exchange": self.exchange_name, "symbol": self.default_symbol}
        )

    def get_ohlcv(
        self,
        symbol: Optional[str] = None,
        timeframe: str = "15m",
        limit: int = 200,
        retries: int = 3
    ) -> pd.DataFrame:
        """
        Obtiene datos OHLCV del exchange con manejo de errores y reintentos.

        Args:
            symbol: Símbolo de trading (ej: BTC/USD)
            timeframe: Intervalo de tiempo (ej: 15m, 1h)
            limit: Número de velas a obtener
            retries: Número de reintentos en caso de error

        Returns:
            DataFrame con columnas [timestamp, open, high, low, close, volume]
        """
        symbol = symbol or self.default_symbol

        for attempt in range(retries):
            try:
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=limit
                )

                df = pd.DataFrame(
                    ohlcv,
                    columns=["timestamp", "open", "high", "low", "close", "volume"]
                )
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)

                logger.log_error(
                    error_type="oracle_success",
                    error_msg=f"Successfully fetched {len(df)} candles for {symbol}",
                    context={
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "rows": len(df),
                        "attempt": attempt + 1
                    }
                )

                return df

            except Exception as e:
                if attempt < retries - 1:
                    logger.log_error(
                        error_type="oracle_retry",
                        error_msg=f"Error fetching data, retrying... (attempt {attempt + 1}/{retries})",
                        context={
                            "symbol": symbol,
                            "timeframe": timeframe,
                            "error": str(e)
                        }
                    )
                    continue
                else:
                    logger.log_error(
                        error_type="oracle_failure",
                        error_msg=f"Failed to fetch data after {retries} attempts",
                        context={
                            "symbol": symbol,
                            "timeframe": timeframe,
                            "error": str(e)
                        }
                    )
                    raise

    def get_current_price(self, symbol: Optional[str] = None) -> float:
        """
        Obtiene el precio actual de un ticker.

        Args:
            symbol: Símbolo de trading

        Returns:
            Precio actual (último trade)
        """
        symbol = symbol or self.default_symbol

        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return float(ticker["last"])
        except Exception as e:
            logger.log_error(
                error_type="oracle_price_error",
                error_msg=f"Failed to get current price for {symbol}",
                context={"symbol": symbol, "error": str(e)}
            )
            raise

if __name__ == "__main__":
    # Test de oracle
    feed = OraclePriceFeed("kraken")
    df = feed.get_ohlcv(limit=5)
    print(df)
    print("last close:", df.iloc[-1]["close"])