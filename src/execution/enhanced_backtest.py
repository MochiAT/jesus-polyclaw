"""
Framework de backtesting mejorado con gestión de riesgo y validación de datos.
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Tuple
from datetime import datetime

from src.data.oracle_prices import OraclePriceFeed
from src.data.features import compute_features
from src.data.data_validator import DataValidator
from src.risk.risk_manager import RiskManager, RiskConfig
from config.trading_config import CONFIG

Side = Literal["YES", "NO", "SKIP"]

@dataclass
class BacktestConfig:
    """Configuración específica de backtesting"""
    timeframe: str = "15m"
    days: int = 7
    horizon_bars: int = 1
    train_test_split: float = 0.7  # 70% train, 30% test
    min_trades_for_significance: int = 20

@dataclass
class BacktestResult:
    """Resultados de backtesting"""
    strategy_name: str
    start_balance: float
    end_balance: float
    total_pnl: float
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    max_drawdown: float
    sharpe_ratio: float
    profit_factor: float
    avg_trade_pnl: float
    trades_history: List[Dict] = field(default_factory=list)

def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """Calcula ratio de Sharpe anualizado"""
    if len(returns) < 2:
        return 0.0

    excess_returns = returns - risk_free_rate
    if excess_returns.std() == 0:
        return 0.0

    return (excess_returns.mean() / excess_returns.std()) * np.sqrt(252)  # Asumiendo trading diario

def outcome_up(close_now: float, close_future: float) -> Optional[bool]:
    """Determina resultado del mercado: True=UP, False=DOWN, None=flat"""
    if close_future > close_now:
        return True
    if close_future < close_now:
        return False
    return None

def payout_for_side(side: Side, up: Optional[bool]) -> Optional[float]:
    """Calcula payout según lado y resultado"""
    if up is None:
        return None
    if side == "YES":
        return 1.0 if up else 0.0
    if side == "NO":
        return 1.0 if (not up) else 0.0
    return None

class EnhancedBacktester:
    """
    Framework de backtesting con gestión de riesgo y validación.
    """

    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()
        self.validator = DataValidator()
        self.risk_config = RiskConfig(
            max_position_size_pct=CONFIG.max_position_size,
            stop_loss_pct=CONFIG.stop_loss_pct,
            take_profit_pct=CONFIG.take_profit_pct,
            max_drawdown_pct=CONFIG.max_drawdown_pct,
            daily_loss_limit_pct=CONFIG.daily_loss_limit
        )

    def run_backtest(self, strategy, timeframe: str = None, days: int = None) -> BacktestResult:
        """
        Ejecuta backtesting de una estrategia.

        Args:
            strategy: Instancia de estrategia con método `decide(row)`
            timeframe: Timeframe para datos OHLCV
            days: Número de días a backtestear

        Returns:
            BacktestResult con métricas y trades
        """
        timeframe = timeframe or self.config.timeframe
        days = days or self.config.days

        # 1. Obtener datos
        feed = OraclePriceFeed(exchange=CONFIG.exchange)
        limit = int((days * 24 * 60) / 15) + 50
        df = feed.get_ohlcv(timeframe=timeframe, limit=limit)

        # 2. Validar datos
        is_valid, validation_report = self.validator.validate_ohlcv(df)
        if not is_valid:
            raise ValueError(f"Data validation failed: {validation_report['reason']}")

        # 3. Calcular features
        df_feat = compute_features(df).dropna().reset_index(drop=True)

        # 4. Dividir train/test
        split_idx = int(len(df_feat) * self.config.train_test_split)
        df_test = df_feat.iloc[split_idx:].copy()

        # 5. Inicializar gestión de riesgo
        risk_manager = RiskManager(config=self.risk_config, initial_balance=CONFIG.start_balance)

        # 6. Ejecutar backtest
        last_i = len(df_test) - 1 - self.config.horizon_bars
        trades_history = []

        for i in range(last_i):
            row = df_test.iloc[i]
            close_now = float(row["close"])
            close_future = float(df_test.iloc[i + self.config.horizon_bars]["close"])
            up = outcome_up(close_now, close_future)

            if up is None:
                continue  # Saltar empates

            # Decidir trade según estrategia
            side: Side = strategy.decide(row)
            if side == "SKIP":
                continue

            # Validar trade según gestión de riesgo
            price = CONFIG.entry_price
            size = risk_manager.calculate_position_size(price)

            is_allowed, reason = risk_manager.validate_trade(
                market_id=f"test_{i}",
                side=side,
                price=price,
                size=size
            )

            if not is_allowed:
                continue

            # Calcular payout
            payout = payout_for_side(side, up)
            if payout is None:
                continue

            # Simular trade
            trade_pnl = (payout - price) * size
            risk_manager.open_position(
                market_id=f"test_{i}",
                side=side,
                price=price,
                size=size
            )

            final_pnl = risk_manager.close_position(
                market_id=f"test_{i}",
                exit_price=payout,
                exit_reason="market_close"
            )

            trades_history.append({
                "index": i,
                "timestamp": row["timestamp"],
                "side": side,
                "entry_price": price,
                "exit_price": payout,
                "size": size,
                "pnl": final_pnl,
                "up": up
            })

        # 7. Calcular métricas
        metrics = risk_manager.get_risk_metrics()
        df_trades = pd.DataFrame(trades_history)

        if not df_trades.empty:
            returns = df_trades['pnl'] / (df_trades['entry_price'] * df_trades['size'])
            wins = (df_trades['pnl'] > 0).sum()
            losses = (df_trades['pnl'] < 0).sum()
            sharpe = calculate_sharpe_ratio(returns)

            gross_profit = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
            gross_loss = abs(df_trades[df_trades['pnl'] < 0]['pnl'].sum())
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        else:
            wins = losses = sharpe = profit_factor = 0
            gross_profit = gross_loss = 0

        return BacktestResult(
            strategy_name=strategy.__class__.__name__,
            start_balance=CONFIG.start_balance,
            end_balance=metrics.current_balance,
            total_pnl=metrics.daily_pnl,
            total_trades=len(trades_history),
            wins=int(wins),
            losses=int(losses),
            win_rate=(wins / len(trades_history) * 100) if trades_history else 0.0,
            max_drawdown=metrics.max_drawdown,
            sharpe_ratio=sharpe,
            profit_factor=profit_factor,
            avg_trade_pnl=metrics.daily_pnl / len(trades_history) if trades_history else 0.0,
            trades_history=trades_history
        )

    def compare_strategies(self, strategies: Dict[str, object], timeframe: str = None, days: int = None) -> Dict[str, BacktestResult]:
        """
        Compara múltiples estrategias y retorna resultados.

        Returns:
            Dict con {nombre_estrategia: BacktestResult}
        """
        results = {}

        for name, strategy in strategies.items():
            try:
                result = self.run_backtest(strategy, timeframe, days)
                results[name] = result
            except Exception as e:
                print(f"Error testing {name}: {str(e)}")

        return results

    def print_comparison(self, results: Dict[str, BacktestResult]):
        """
        Imprime comparación tabular de resultados.
        """
        print("\n" + "="*80)
        print("BACKTESTING RESULTS COMPARISON")
        print("="*80)

        for name, result in results.items():
            print(f"\n📊 Strategy: {name}")
            print("-" * 40)
            print(f"  Balance: ${result.start_balance:.2f} → ${result.end_balance:.2f}")
            print(f"  PnL: ${result.total_pnl:+.2f}")
            print(f"  Trades: {result.total_trades} (Wins: {result.wins}, Losses: {result.losses})")
            print(f"  Win Rate: {result.win_rate:.2f}%")
            print(f"  Max Drawdown: {result.max_drawdown*100:.2f}%")
            print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
            print(f"  Profit Factor: {result.profit_factor:.2f}")
            print(f"  Avg Trade PnL: ${result.avg_trade_pnl:+.2f}")

        print("\n" + "="*80)

# ---------- ESTRATEGIAS DE EJEMPLO ----------

class BaselineDirectionStrategy:
    """Estrategia baseline basada en momentum simple"""
    def decide(self, row) -> Side:
        m = row["momentum_3"]
        if m > 0:
            return "YES"
        if m < 0:
            return "NO"
        return "SKIP"

class RSIReversionStrategy:
    """Estrategia de reversión a la media usando RSI"""
    def __init__(self, low=30.0, high=70.0):
        self.low = low
        self.high = high

    def decide(self, row) -> Side:
        rsi = row["rsi_14"]
        if rsi < self.low:
            return "YES"
        if rsi > self.high:
            return "NO"
        return "SKIP"

class CombinedStrategy:
    """Estrategia combinada: RSI + Momentum"""
    def __init__(self, rsi_low=30.0, rsi_high=70.0):
        self.rsi_low = rsi_low
        self.rsi_high = rsi_high

    def decide(self, row) -> Side:
        rsi = row["rsi_14"]
        momentum = row["momentum_3"]

        # Ambos indicadores deben estar de acuerdo
        if rsi < self.rsi_low and momentum < 0:
            return "YES"
        if rsi > self.rsi_high and momentum > 0:
            return "NO"

        return "SKIP"

# ---------- MAIN ----------

def main():
    """Ejecuta comparación de estrategias"""
    backtester = EnhancedBacktester()

    strategies = {
        "baseline_direction": BaselineDirectionStrategy(),
        "rsi_reversion": RSIReversionStrategy(low=30, high=70),
        "combined_rsi_momentum": CombinedStrategy(rsi_low=30, rsi_high=70),
    }

    print("🚀 Running enhanced backtesting with risk management...")
    results = backtester.compare_strategies(strategies)
    backtester.print_comparison(results)

    # Guardar resultado en archivo
    import json
    for name, result in results.items():
        filename = f"results_{name}.json"
        with open(filename, 'w') as f:
            json.dump({
                "strategy": result.strategy_name,
                "metrics": {
                    "start_balance": result.start_balance,
                    "end_balance": result.end_balance,
                    "total_pnl": result.total_pnl,
                    "total_trades": result.total_trades,
                    "wins": result.wins,
                    "losses": result.losses,
                    "win_rate": result.win_rate,
                    "max_drawdown": result.max_drawdown,
                    "sharpe_ratio": result.sharpe_ratio,
                    "profit_factor": result.profit_factor,
                    "avg_trade_pnl": result.avg_trade_pnl
                },
                "trades": result.trades_history
            }, f, indent=2, default=str)

if __name__ == "__main__":
    main()