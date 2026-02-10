"""
Sistema de logging estructurado para trazabilidad de decisiones y debugging.
"""
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

class TradingLogger:
    """
    Logger especializado para trading con estructuración de datos.
    Permite tracking detallado de decisiones, trades y estado del sistema.
    """

    def __init__(self, name: str = "polyclaw_jesus", log_file: str = None, level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))

        # Formateador estándar
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # File handler si se especifica
        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        # Trade decisions log (separate structured file)
        self.decisions_log = []
        self.trades_log = []

    def log_market_selection(self, market_id: str, slug: str, end_epoch: int,
                            confidence: float, features: Dict[str, Any]):
        """Log de selección de mercado con features y confianza"""
        self.logger.info(f"Market selected: {slug} (ID: {market_id})")
        self._append_structured_log({
            "event": "market_selection",
            "timestamp": datetime.utcnow().isoformat(),
            "market_id": market_id,
            "slug": slug,
            "end_epoch": end_epoch,
            "confidence": confidence,
            "features": features
        })

    def log_trade_decision(self, market_id: str, side: str, price: float,
                           size: float, reason: str, confidence: float = 0.0):
        """Log de decisión de trade con contexto completo"""
        self.logger.info(f"Trade decision: {side} {size}@{price} - {reason}")
        self._append_structured_log({
            "event": "trade_decision",
            "timestamp": datetime.utcnow().isoformat(),
            "market_id": market_id,
            "side": side,
            "price": price,
            "size": size,
            "confidence": confidence,
            "reason": reason
        })

    def log_trade_execution(self, trade_id: str, market_id: str, side: str,
                           executed_price: float, executed_size: float,
                           status: str):
        """Log de ejecución de trade"""
        self.logger.info(f"Trade executed: {trade_id} - {status}")
        self.trades_log.append({
            "trade_id": trade_id,
            "timestamp": datetime.utcnow().isoformat(),
            "market_id": market_id,
            "side": side,
            "executed_price": executed_price,
            "executed_size": executed_size,
            "status": status
        })

    def log_risk_alert(self, alert_type: str, details: Dict[str, Any]):
        """Log de alertas de riesgo"""
        self.logger.warning(f"Risk alert: {alert_type} - {details}")
        self._append_structured_log({
            "event": "risk_alert",
            "timestamp": datetime.utcnow().isoformat(),
            "alert_type": alert_type,
            "details": details
        })

    def log_backtest_result(self, strategy_name: str, metrics: Dict[str, float]):
        """Log de resultados de backtest"""
        self.logger.info(f"Backtest completed: {strategy_name}")
        self._append_structured_log({
            "event": "backtest_result",
            "timestamp": datetime.utcnow().isoformat(),
            "strategy": strategy_name,
            "metrics": metrics
        })

    def log_error(self, error_type: str, error_msg: str, context: Dict[str, Any] = None):
        """Log de errores con contexto"""
        self.logger.error(f"Error: {error_type} - {error_msg}")
        self._append_structured_log({
            "event": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": error_type,
            "error_message": error_msg,
            "context": context or {}
        })

    def _append_structured_log(self, log_entry: Dict[str, Any]):
        """Añade entrada a logs estructurados"""
        self.decisions_log.append(log_entry)

    def get_recent_decisions(self, limit: int = 10) -> list:
        """Retorna las últimas decisiones estructuradas"""
        return self.decisions_log[-limit:]

    def get_all_trades(self) -> list:
        """Retorna todos los trades ejecutados"""
        return self.trades_log

    def save_structured_logs(self, filepath: str):
        """Guarda logs estructurados a archivo JSON"""
        with open(filepath, 'w') as f:
            json.dump({
                "decisions": self.decisions_log,
                "trades": self.trades_log
            }, f, indent=2)

# Logger global
logger = TradingLogger()