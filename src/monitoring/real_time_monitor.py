"""
Sistema de monitoreo en tiempo real para tracking del estado del sistema.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import json
from pathlib import Path

@dataclass
class SystemStatus:
    """Estado del sistema"""
    timestamp: str
    balance: float
    equity_peak: float
    current_drawdown: float
    max_drawdown: float
    daily_pnl: float
    open_positions: int
    risk_level: str
    last_trade_time: Optional[str] = None
    last_trade_result: Optional[str] = None
    last_market_selected: Optional[str] = None

@dataclass
class Alert:
    """Alerta de sistema"""
    timestamp: str
    level: str  # "INFO", "WARNING", "CRITICAL"
    category: str  # "RISK", "SYSTEM", "MARKET", "ERROR"
    message: str
    details: Dict = field(default_factory=dict)

class RealTimeMonitor:
    """
    Monitor en tiempo real del sistema de trading.
    Permite tracking de estado y generación de alertas.
    """

    def __init__(self, alert_on_drawdown: bool = True, alert_on_trades: bool = False):
        self.alert_on_drawdown = alert_on_drawdown
        self.alert_on_trades = alert_on_trades
        self.alerts: List[Alert] = []
        self.status_history: List[SystemStatus] = []
        self.alert_rules = {
            "drawdown_warning": 0.10,  # 10% drawdown = WARNING
            "drawdown_critical": 0.15,  # 15% drawdown = CRITICAL
            "daily_loss_warning": 0.02,  # 2% pérdida diaria = WARNING
            "daily_loss_critical": 0.03,  # 3% pérdida diaria = CRITICAL
        }

    def update_status(
        self,
        balance: float,
        equity_peak: float,
        current_drawdown: float,
        max_drawdown: float,
        daily_pnl: float,
        open_positions: int,
        risk_level: str
    ):
        """
        Actualiza estado del sistema y verifica alertas.
        """
        status = SystemStatus(
            timestamp=datetime.utcnow().isoformat(),
            balance=balance,
            equity_peak=equity_peak,
            current_drawdown=current_drawdown,
            max_drawdown=max_drawdown,
            daily_pnl=daily_pnl,
            open_positions=open_positions,
            risk_level=risk_level
        )

        # Mantener referencia a valores anteriores si existen
        if self.status_history:
            last_status = self.status_history[-1]
            status.last_trade_time = last_status.last_trade_time
            status.last_trade_result = last_status.last_trade_result
            status.last_market_selected = last_status.last_market_selected

        self.status_history.append(status)
        self._check_alerts(status)

        # Mantener solo historial reciente (últimas 100 entradas)
        if len(self.status_history) > 100:
            self.status_history = self.status_history[-100:]

    def _check_alerts(self, status: SystemStatus):
        """Verifica condiciones de alerta"""
        # Drawdown alerts
        if self.alert_on_drawdown:
            if status.current_drawdown >= self.alert_rules["drawdown_critical"]:
                self._add_alert(
                    level="CRITICAL",
                    category="RISK",
                    message=f"Critical drawdown: {status.current_drawdown*100:.2f}%",
                    details={"current_drawdown": status.current_drawdown}
                )
            elif status.current_drawdown >= self.alert_rules["drawdown_warning"]:
                self._add_alert(
                    level="WARNING",
                    category="RISK",
                    message=f"High drawdown warning: {status.current_drawdown*100:.2f}%",
                    details={"current_drawdown": status.current_drawdown}
                )

        # Daily loss alerts
        daily_loss_pct = abs(status.daily_pnl) / status.balance if status.daily_pnl < 0 else 0
        if daily_loss_pct >= self.alert_rules["daily_loss_critical"]:
            self._add_alert(
                level="CRITICAL",
                category="RISK",
                message=f"Critical daily loss: {daily_loss_pct*100:.2f}%",
                details={"daily_pnl": status.daily_pnl, "balance": status.balance}
            )
        elif daily_loss_pct >= self.alert_rules["daily_loss_warning"]:
            self._add_alert(
                level="WARNING",
                category="RISK",
                message=f"High daily loss warning: {daily_loss_pct*100:.2f}%",
                details={"daily_pnl": status.daily_pnl, "balance": status.balance}
            )

    def _add_alert(self, level: str, category: str, message: str, details: Dict = None):
        """Añade alerta al sistema"""
        alert = Alert(
            timestamp=datetime.utcnow().isoformat(),
            level=level,
            category=category,
            message=message,
            details=details or {}
        )
        self.alerts.append(alert)

        # Mantener solo alertas recientes (últimas 50)
        if len(self.alerts) > 50:
            self.alerts = self.alerts[-50:]

    def log_trade(self, market_id: str, side: str, pnl: float):
        """Registra un trade ejecutado"""
        if self.status_history:
            status = self.status_history[-1]
            status.last_trade_time = datetime.utcnow().isoformat()
            status.last_trade_result = f"{side} ${pnl:+.2f}"
            status.last_market_selected = market_id

            if self.alert_on_trades:
                level = "INFO" if pnl > 0 else "WARNING"
                self._add_alert(
                    level=level,
                    category="SYSTEM",
                    message=f"Trade executed: {side} ${pnl:+.2f}",
                    details={"market_id": market_id, "side": side, "pnl": pnl}
                )

    def log_market_selection(self, market_id: str, slug: str, score: float):
        """Registra selección de mercado"""
        if self.status_history:
            status = self.status_history[-1]
            status.last_market_selected = slug

            self._add_alert(
                level="INFO",
                category="MARKET",
                message=f"Market selected: {slug} (score: {score:.2f})",
                details={"market_id": market_id, "slug": slug, "score": score}
            )

    def get_current_status(self) -> Optional[SystemStatus]:
        """Retorna el estado más reciente"""
        return self.status_history[-1] if self.status_history else None

    def get_recent_alerts(self, level: str = None, limit: int = 10) -> List[Alert]:
        """Retorna alertas recientes, opcionalmente filtradas por nivel"""
        alerts = self.alerts

        if level:
            alerts = [a for a in alerts if a.level == level]

        return alerts[-limit:]

    def get_status_summary(self) -> Dict:
        """Retorna resumen del estado actual"""
        status = self.get_current_status()
        if not status:
            return {"status": "no_data"}

        critical_alerts = [a for a in self.alerts if a.level == "CRITICAL"]
        warning_alerts = [a for a in self.alerts if a.level == "WARNING"]

        return {
            "timestamp": status.timestamp,
            "balance": status.balance,
            "equity_peak": status.equity_peak,
            "current_drawdown_pct": f"{status.current_drawdown*100:.2f}%",
            "max_drawdown_pct": f"{status.max_drawdown*100:.2f}%",
            "daily_pnl": status.daily_pnl,
            "daily_pnl_pct": f"{(status.daily_pnl/status.balance)*100:.2f}%",
            "open_positions": status.open_positions,
            "risk_level": status.risk_level,
            "critical_alerts": len(critical_alerts),
            "warning_alerts": len(warning_alerts),
            "last_trade": status.last_trade_result,
            "last_market": status.last_market_selected
        }

    def generate_report(self) -> str:
        """Genera reporte legible del estado del sistema"""
        summary = self.get_status_summary()

        report = [
            "="*60,
            "📊 SYSTEM MONITORING REPORT",
            "="*60,
            f"Timestamp: {summary['timestamp']}",
            f"",
            f"💰 Balance: ${summary['balance']:.2f}",
            f"📈 Equity Peak: ${summary['equity_peak']:.2f}",
            f"📉 Current Drawdown: {summary['current_drawdown_pct']}",
            f"📉 Max Drawdown: {summary['max_drawdown_pct']}",
            f"",
            f"💵 Daily PnL: ${summary['daily_pnl']:+.2f} ({summary['daily_pnl_pct']})",
            f"",
            f"🎯 Open Positions: {summary['open_positions']}",
            f"⚠️  Risk Level: {summary['risk_level']}",
            f"",
            f"🚨 Critical Alerts: {summary['critical_alerts']}",
            f"⚠️  Warning Alerts: {summary['warning_alerts']}",
            f"",
            f"🔄 Last Trade: {summary['last_trade']}",
            f"📊 Last Market: {summary['last_market']}",
            "="*60
        ]

        return "\n".join(report)

    def save_status_to_file(self, filepath: str):
        """Guarda estado actual a archivo JSON"""
        summary = self.get_status_summary()

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(summary, f, indent=2)

    def save_alerts_to_file(self, filepath: str):
        """Guarda alertas a archivo JSON"""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump([{
                "timestamp": a.timestamp,
                "level": a.level,
                "category": a.category,
                "message": a.message,
                "details": a.details
            } for a in self.alerts], f, indent=2)