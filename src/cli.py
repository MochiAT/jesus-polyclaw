#!/usr/bin/env python3
"""
CLI principal para Polyclaw-Jesus.
Permite ejecutar backtesting, paper trading y análisis de mercado.
"""
import argparse
import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.oracle_prices import OraclePriceFeed
from src.data.features import compute_features
from src.data.enhanced_market_selector import MarketSelector
from src.data.data_validator import DataValidator
from src.execution.enhanced_backtest import EnhancedBacktester
from src.risk.risk_manager import RiskManager
from src.monitoring.real_time_monitor import RealTimeMonitor
from src.utils.logger import logger

# Importar estrategias
from src.strategy.baseline_strategy import BaselineStrategy
from src.strategy.rsi_strategy import RSIStrategy
from src.strategy.combined_strategy import CombinedStrategy, AdaptiveRSIStrategy

def run_backtest(args):
    """
    Ejecuta backtesting de estrategias.
    """
    print("🚀 Starting backtest...")

    # Crear backtester
    backtester = EnhancedBacktester()

    # Mapeo de estrategias
    strategies = {
        "baseline": BaselineStrategy(),
        "rsi": RSIStrategy(),
        "combined": CombinedStrategy(),
        "adaptive_rsi": AdaptiveRSIStrategy(),
    }

    # Filtrar estrategias a testear
    if args.strategy and args.strategy in strategies:
        strategies_to_test = {args.strategy: strategies[args.strategy]}
    else:
        strategies_to_test = strategies

    # Ejecutar backtest
    results = backtester.compare_strategies(
        strategies_to_test,
        timeframe=args.timeframe,
        days=args.days
    )

    # Mostrar resultados
    backtester.print_comparison(results)

    # Guardar logs
    logger.save_structured_logs("backtest_logs.json")

    print("\n✅ Backtest completed!")
    return 0

def select_market(args):
    """
    Selecciona el mejor mercado actual.
    """
    print("🎯 Selecting best market...")

    selector = MarketSelector(
        assets=args.assets.split(",") if args.assets else None,
        timeframes=args.timeframes.split(",") if args.timeframes else None,
        min_liquidity=args.min_liquidity,
        max_spread_pct=args.max_spread_pct
    )

    market = selector.select_best_market()

    if market:
        print("\n✅ Market selected:")
        print(f"  Slug: {market['slug']}")
        print(f"  Market ID: {market['market_id']}")
        print(f"  Ends at: {market['end_utc']}")
        print(f"  Score: {market['score']:.3f}")
        print(f"  Quality: {market['quality_report']}")

        # Log de selección
        logger.log_market_selection(
            market_id=market['market_id'],
            slug=market['slug'],
            end_epoch=market['end_epoch'],
            confidence=market['score'],
            features=market['quality_report']
        )

        # Mostrar estadísticas
        stats = selector.get_selection_stats()
        print(f"\n📊 Selection stats:")
        print(f"  Total selections: {stats['total_selections']}")
        print(f"  Average score: {stats['average_score']:.3f}")

        return 0
    else:
        print("\n❌ No suitable market found")
        return 1

def run_paper_trading(args):
    """
    Ejecuta simulación de paper trading.
    """
    print("📈 Starting paper trading simulation...")
    print("⚠️  Note: This is a simulation. No real trades will be executed.")

    # Inicializar componentes
    feed = OraclePriceFeed(exchange=args.exchange)
    validator = DataValidator()
    risk_manager = RiskManager(initial_balance=args.balance)
    monitor = RealTimeMonitor(alert_on_drawdown=True, alert_on_trades=True)

    # Estrategia a usar
    strategy_map = {
        "baseline": BaselineStrategy(),
        "rsi": RSIStrategy(),
        "combined": CombinedStrategy(),
        "adaptive_rsi": AdaptiveRSIStrategy(),
    }
    strategy = strategy_map.get(args.strategy, CombinedStrategy())

    print(f"  Strategy: {args.strategy}")
    print(f"  Timeframe: {args.timeframe}")
    print(f"  Initial balance: ${args.balance:.2f}")

    # Obtener datos
    df = feed.get_ohlcv(timeframe=args.timeframe, limit=500)

    # Validar datos
    is_valid, validation_report = validator.validate_ohlcv(df)
    if not is_valid:
        print(f"❌ Data validation failed: {validation_report['reason']}")
        return 1

    # Calcular features
    df_feat = compute_features(df)

    # Simular trades (últimos 50 candles)
    recent_df = df_feat.tail(50)

    for idx, row in recent_df.iterrows():
        # Decidir trade
        decision = strategy.decide(row.to_dict())

        if decision in ["YES", "NO"]:
            # Simular trade con riesgo
            price = 0.5  # Precio asumido
            size = risk_manager.calculate_position_size(price)

            is_allowed, reason = risk_manager.validate_trade(
                market_id=f"paper_{idx}",
                side=decision,
                price=price,
                size=size
            )

            if is_allowed:
                # Simular resultado (random para demo)
                import random
                outcome_price = random.choice([1.0, 0.0])
                pnl = (outcome_price - price) * size

                risk_manager.open_position(
                    market_id=f"paper_{idx}",
                    side=decision,
                    price=price,
                    size=size
                )

                final_pnl = risk_manager.close_position(
                    market_id=f"paper_{idx}",
                    exit_price=outcome_price
                )

                monitor.log_trade(
                    market_id=f"paper_{idx}",
                    side=decision,
                    pnl=final_pnl
                )

                # Actualizar monitor
                metrics = risk_manager.get_risk_metrics()
                monitor.update_status(
                    balance=metrics.current_balance,
                    equity_peak=metrics.equity_peak,
                    current_drawdown=metrics.current_drawdown,
                    max_drawdown=metrics.max_drawdown,
                    daily_pnl=metrics.daily_pnl,
                    open_positions=len(risk_manager.open_positions),
                    risk_level=risk_manager.risk_level.value
                )

    # Mostrar resultados finales
    print("\n" + monitor.generate_report())
    print("\n✅ Paper trading simulation completed!")

    # Guardar logs
    logger.save_structured_logs("paper_trading_logs.json")
    monitor.save_status_to_file("paper_trading_status.json")

    return 0

def main():
    """
    Función principal del CLI.
    """
    parser = argparse.ArgumentParser(
        description="Polyclaw-Jesus: Enhanced crypto trading system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run backtest for all strategies
  python src/cli.py backtest

  # Run backtest for specific strategy
  python src/cli.py backtest --strategy rsi --timeframe 15m --days 14

  # Select best current market
  python src/cli.py select-market --assets btc,eth --timeframes 15m,30m

  # Run paper trading simulation
  python src/cli.py paper-trading --strategy combined --balance 1000
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Subcomando: backtest
    backtest_parser = subparsers.add_parser("backtest", help="Run backtesting")
    backtest_parser.add_argument("--strategy", choices=["baseline", "rsi", "combined", "adaptive_rsi"],
                                help="Strategy to backtest (default: all)")
    backtest_parser.add_argument("--timeframe", default="15m", help="Timeframe (default: 15m)")
    backtest_parser.add_argument("--days", type=int, default=7, help="Days to backtest (default: 7)")

    # Subcomando: select-market
    market_parser = subparsers.add_parser("select-market", help="Select best market")
    market_parser.add_argument("--assets", help="Comma-separated assets (e.g., btc,eth,xrp)")
    market_parser.add_argument("--timeframes", help="Comma-separated timeframes (e.g., 15m,30m,1h)")
    market_parser.add_argument("--min-liquidity", type=float, default=1000.0,
                              help="Minimum liquidity (default: 1000)")
    market_parser.add_argument("--max-spread-pct", type=float, default=0.05,
                              help="Max spread percentage (default: 0.05)")

    # Subcomando: paper-trading
    paper_parser = subparsers.add_parser("paper-trading", help="Run paper trading simulation")
    paper_parser.add_argument("--strategy", choices=["baseline", "rsi", "combined", "adaptive_rsi"],
                              default="combined", help="Strategy to use (default: combined)")
    paper_parser.add_argument("--timeframe", default="15m", help="Timeframe (default: 15m)")
    paper_parser.add_argument("--exchange", default="kraken", help="Exchange (default: kraken)")
    paper_parser.add_argument("--balance", type=float, default=1000.0, help="Initial balance (default: 1000)")

    args = parser.parse_args()

    if args.command == "backtest":
        return run_backtest(args)
    elif args.command == "select-market":
        return select_market(args)
    elif args.command == "paper-trading":
        return run_paper_trading(args)
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())