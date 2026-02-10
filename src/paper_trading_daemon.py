#!/usr/bin/env python3
"""
Daemon de paper trading autónomo para Polyclaw-Jesus.
Corre continuamente durante el tiempo especificado sin usar LLM.
"""
import sys
import time
import json
from datetime import datetime, timezone
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.oracle_prices import OraclePriceFeed
from src.data.features import compute_features
from src.data.enhanced_market_selector import MarketSelector
from src.data.data_validator import DataValidator
from src.risk.risk_manager import RiskManager
from src.monitoring.real_time_monitor import RealTimeMonitor
from src.utils.logger import logger

# Importar estrategias
from src.strategy.baseline_strategy import BaselineStrategy
from src.strategy.rsi_strategy import RSIStrategy
from src.strategy.combined_strategy import CombinedStrategy
from src.strategy.combined_strategy import AdaptiveRSIStrategy


class PaperTradingDaemon:
    """
    Daemon de paper trading que corre autónomamente.
    """

    def __init__(self, duration_hours: int = 2, strategy_name: str = "combined"):
        self.duration_seconds = duration_hours * 3600
        self.start_time = time.time()
        self.end_time = self.start_time + self.duration_seconds

        # Estrategia a usar
        strategy_map = {
            "baseline": BaselineStrategy(),
            "rsi": RSIStrategy(),
            "combined": CombinedStrategy(),
            "adaptive_rsi": AdaptiveRSIStrategy(),
        }
        self.strategy = strategy_map.get(strategy_name, CombinedStrategy())

        # Inicializar componentes
        self.feed = OraclePriceFeed(exchange="kraken")
        self.validator = DataValidator()
        self.market_selector = MarketSelector()
        self.risk_manager = RiskManager(initial_balance=1000.0)
        self.monitor = RealTimeMonitor(alert_on_drawdown=True, alert_on_trades=True)

        # Métricas de sesión
        self.markets_selected = 0
        self.trades_executed = 0
        self.decisions_made = 0
        self.errors = 0

        print(f"🚀 Paper Trading Daemon iniciado")
        print(f"⏱️  Duración: {duration_hours} horas")
        print(f"📊 Estrategia: {strategy_name}")
        print(f"💰 Balance inicial: ${self.risk_manager.balance:.2f}")
        print(f"⏰ Inicio: {datetime.fromtimestamp(self.start_time, tz=timezone.utc)}")
        print(f"⏰ Fin: {datetime.fromtimestamp(self.end_time, tz=timezone.utc)}")
        print("=" * 60)

    def run(self):
        """
        Ejecuta el daemon de paper trading.
        """
        cycle_count = 0
        check_interval = 300  # 5 minutos entre ciclos

        while time.time() < self.end_time:
            cycle_count += 1
            current_time = time.time()
            remaining_time = self.end_time - current_time
            remaining_minutes = remaining_time / 60

            print(f"\n🔄 Ciclo #{cycle_count}")
            print(f"⏰ Tiempo restante: {remaining_minutes:.1f} minutos ({remaining_minutes/60:.1f} horas)")

            try:
                # 1. Seleccionar mejor mercado
                print("🎯 Buscando mejor mercado...")
                market = self.market_selector.select_best_market()

                if not market:
                    print("⚠️  No se encontró mercado adecuado")
                    time.sleep(check_interval)
                    continue

                self.markets_selected += 1
                print(f"✅ Mercado seleccionado: {market['slug']}")
                print(f"   Score: {market['score']:.3f}")
                print(f"   Termina: {market['end_utc']}")

                # Log de selección
                logger.log_market_selection(
                    market_id=market['market_id'],
                    slug=market['slug'],
                    end_epoch=market['end_epoch'],
                    confidence=market['score'],
                    features=market['quality_report']
                )

                self.monitor.log_market_selection(
                    market_id=market['market_id'],
                    slug=market['slug'],
                    score=market['score']
                )

                # 2. Obtener datos de precios
                print("📊 Obteniendo datos de precios...")
                df = self.feed.get_ohlcv(timeframe="15m", limit=100)

                # Validar datos
                is_valid, validation_report = self.validator.validate_ohlcv(df)
                if not is_valid:
                    print(f"⚠️  Validación fallida: {validation_report['reason']}")
                    self.errors += 1
                    time.sleep(check_interval)
                    continue

                # Calcular features
                df_feat = compute_features(df)
                latest_features = df_feat.iloc[-1].to_dict()

                print(f"   Último precio: ${latest_features['close']:.2f}")
                print(f"   RSI: {latest_features['rsi_14']:.2f}")

                # 3. Tomar decisión
                print(f"🧠 Tomando decisión con estrategia {self.strategy.__class__.__name__}...")
                decision = self.strategy.decide(latest_features)
                self.decisions_made += 1

                if decision in ["YES", "NO"]:
                    print(f"   Decisión: {decision}")

                    # Calcular tamaño de posición
                    price = 0.5  # Precio asumido
                    size = self.risk_manager.calculate_position_size(price)

                    # Validar trade según riesgo
                    is_allowed, reason = self.risk_manager.validate_trade(
                        market_id=market['market_id'],
                        side=decision,
                        price=price,
                        size=size
                    )

                    if is_allowed:
                        # Simular trade (random para paper trading)
                        import random
                        random.seed(hash(str(datetime.now())))

                        # Outcome basado en dirección de tendencia (momentum)
                        momentum = latest_features['momentum_3']
                        if decision == "YES":
                            win_prob = 0.5 + (momentum * 50)  # Ajustado por momentum
                        else:
                            win_prob = 0.5 - (momentum * 50)

                        win_prob = max(0.1, min(0.9, win_prob))
                        outcome_price = 1.0 if random.random() < win_prob else 0.0

                        # Abrir posición
                        self.risk_manager.open_position(
                            market_id=market['market_id'],
                            side=decision,
                            price=price,
                            size=size
                        )

                        # Simular outcome
                        final_pnl = self.risk_manager.close_position(
                            market_id=market['market_id'],
                            exit_price=outcome_price
                        )

                        self.trades_executed += 1
                        print(f"   ✅ Trade ejecutado: {decision} {size}@{price} → ${final_pnl:+.2f}")

                        # Log de trade
                        logger.log_trade_decision(
                            market_id=market['market_id'],
                            side=decision,
                            price=price,
                            size=size,
                            reason=f"Strategy signal, outcome: {outcome_price}",
                            confidence=0.7
                        )

                        logger.log_trade_execution(
                            trade_id=f"trade_{self.trades_executed}",
                            market_id=market['market_id'],
                            side=decision,
                            executed_price=price,
                            executed_size=size,
                            status="completed"
                        )

                        self.monitor.log_trade(
                            market_id=market['market_id'],
                            side=decision,
                            pnl=final_pnl
                        )

                    else:
                        print(f"   ⚠️  Trade rechazado por riesgo: {reason}")

                else:
                    print(f"   Decisión: SKIP (sin señal clara)")

                # 4. Actualizar monitor
                metrics = self.risk_manager.get_risk_metrics()
                self.monitor.update_status(
                    balance=metrics.current_balance,
                    equity_peak=metrics.equity_peak,
                    current_drawdown=metrics.current_drawdown,
                    max_drawdown=metrics.max_drawdown,
                    daily_pnl=metrics.daily_pnl,
                    open_positions=len(self.risk_manager.open_positions),
                    risk_level=self.risk_manager.risk_level.value
                )

                # 5. Mostrar resumen de sesión
                print(f"\n📊 Resumen de sesión:")
                print(f"   Balance actual: ${metrics.current_balance:.2f}")
                print(f"   PnL total: ${metrics.daily_pnl:+.2f}")
                print(f"   Trades ejecutados: {self.trades_executed}")
                print(f"   Mercados seleccionados: {self.markets_selected}")
                print(f"   Errores: {self.errors}")

            except Exception as e:
                self.errors += 1
                print(f"❌ Error en ciclo {cycle_count}: {str(e)}")
                logger.log_error(
                    error_type="daemon_error",
                    error_msg=str(e),
                    context={"cycle": cycle_count}
                )

            # Esperar hasta el siguiente ciclo
            print(f"\n⏳ Esperando {check_interval/60:.0f} minutos hasta el próximo ciclo...")
            time.sleep(check_interval)

        # Guardar reporte final
        self.generate_final_report()

    def generate_final_report(self):
        """
        Genera reporte final de la sesión de paper trading.
        """
        metrics = self.risk_manager.get_risk_metrics()
        duration_hours = (time.time() - self.start_time) / 3600

        print("\n" + "=" * 60)
        print("📊 REPORT FINAL DE PAPER TRADING")
        print("=" * 60)

        print(f"\n⏰ Duración: {duration_hours:.2f} horas")
        print(f"💰 Balance inicial: $1000.00")
        print(f"💰 Balance final: ${metrics.current_balance:.2f}")
        print(f"💵 PnL total: ${metrics.daily_pnl:+.2f}")
        print(f"📈 PnL %: {(metrics.daily_pnl / 1000.0) * 100:.2f}%")

        print(f"\n📊 Métricas de sesión:")
        print(f"   Mercados seleccionados: {self.markets_selected}")
        print(f"   Trades ejecutados: {self.trades_executed}")
        print(f"   Decisiones tomadas: {self.decisions_made}")
        print(f"   Errores: {self.errors}")

        if self.trades_executed > 0:
            trades_log = logger.get_all_trades()
            wins = sum(1 for t in trades_log if float(t.get('executed_price', 0)) > 0.5)
            losses = len(trades_log) - wins
            win_rate = (wins / len(trades_log) * 100) if trades_log else 0

            print(f"\n📈 Métricas de trading:")
            print(f"   Wins: {wins}")
            print(f"   Losses: {losses}")
            print(f"   Win rate: {win_rate:.2f}%")
            print(f"   Avg trade PnL: ${metrics.daily_pnl / len(trades_log):+.2f}")

        print(f"\n🛡️ Métricas de riesgo:")
        print(f"   Drawdown actual: {metrics.current_drawdown * 100:.2f}%")
        print(f"   Drawdown máximo: {metrics.max_drawdown * 100:.2f}%")
        print(f"   Nivel de riesgo: {metrics.risk_level.value}")

        print(f"\n📋 Alertas generadas:")
        critical_alerts = self.monitor.get_recent_alerts(level="CRITICAL", limit=10)
        warning_alerts = self.monitor.get_recent_alerts(level="WARNING", limit=10)
        print(f"   Críticas: {len(critical_alerts)}")
        print(f"   Warning: {len(warning_alerts)}")

        # Guardar reportes a archivos
        report_data = {
            "session_info": {
                "duration_hours": duration_hours,
                "start_time": self.start_time,
                "end_time": time.time(),
                "strategy": self.strategy.__class__.__name__
            },
            "performance": {
                "initial_balance": 1000.0,
                "final_balance": metrics.current_balance,
                "total_pnl": metrics.daily_pnl,
                "pnl_pct": (metrics.daily_pnl / 1000.0) * 100
            },
            "session_stats": {
                "markets_selected": self.markets_selected,
                "trades_executed": self.trades_executed,
                "decisions_made": self.decisions_made,
                "errors": self.errors
            },
            "risk_metrics": {
                "current_drawdown": metrics.current_drawdown,
                "max_drawdown": metrics.max_drawdown,
                "risk_level": metrics.risk_level.value
            },
            "trades": logger.get_all_trades()
        }

        # Guardar JSON
        with open("paper_trading_report.json", "w") as f:
            json.dump(report_data, f, indent=2, default=str)

        # Guardar logs estructurados
        logger.save_structured_logs("paper_trading_logs.json")

        # Guardar reporte de monitor
        self.monitor.save_status_to_file("paper_trading_status.json")
        self.monitor.save_alerts_to_file("paper_trading_alerts.json")

        print("\n" + "=" * 60)
        print("📁 Reportes guardados:")
        print("   📄 paper_trading_report.json")
        print("   📄 paper_trading_logs.json")
        print("   📄 paper_trading_status.json")
        print("   📄 paper_trading_alerts.json")
        print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Paper Trading Daemon")
    parser.add_argument("--duration", type=int, default=2,
                       help="Duración en horas (default: 2)")
    parser.add_argument("--strategy", choices=["baseline", "rsi", "combined", "adaptive_rsi"],
                       default="combined", help="Estrategia a usar (default: combined)")

    args = parser.parse_args()

    daemon = PaperTradingDaemon(
        duration_hours=args.duration,
        strategy_name=args.strategy
    )

    try:
        daemon.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Daemon interrumpido por usuario")
        daemon.generate_final_report()