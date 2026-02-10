"""
Selector de mercados mejorado con análisis de liquidez y validación robusta.
"""
import os
import time
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple
import requests

BASE = os.getenv("GAMMA_BASE_URL", "https://gamma-api.polymarket.com")

class MarketSelector:
    """
    Selector inteligente de mercados con múltiples criterios de validación.
    """

    def __init__(
        self,
        assets: List[str] = None,
        timeframes: List[str] = None,
        prefix: str = "updown",
        min_liquidity: float = 1000.0,
        max_spread_pct: float = 0.05,
        max_markets_to_check: int = 5000
    ):
        self.assets = assets or ["btc", "eth", "xrp"]
        self.timeframes = timeframes or ["15m", "30m", "1h"]
        self.prefix = prefix
        self.min_liquidity = min_liquidity
        self.max_spread_pct = max_spread_pct
        self.max_markets_to_check = max_markets_to_check
        self.selection_history = []

    def fetch_events(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Fetch eventos desde la API de Polymarket.
        """
        params = {
            "active": "true",
            "closed": "false",
            "archived": "false",
            "limit": limit,
            "offset": offset,
            "order": "startTime",
            "ascending": "false",
        }
        try:
            r = requests.get(f"{BASE}/events", params=params, timeout=25)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            raise Exception(f"Failed to fetch events: {str(e)}")

    def parse_epoch_from_slug(self, slug: str) -> Optional[int]:
        """
        Extrae epoch del slug del mercado.
        """
        try:
            return int(slug.split("-")[-1])
        except Exception:
            return None

    def is_candidate(self, event: Dict) -> bool:
        """
        Verifica si un evento cumple con criterios básicos de selección.
        """
        slug = (event.get("slug") or "").lower()

        # Verificar prefijo
        if self.prefix not in slug:
            return False

        # Verificar activos
        if not any(asset in slug for asset in self.assets):
            return False

        # Verificar timeframes
        if not any(tf in slug for tf in self.timeframes):
            return False

        return True

    def validate_market_quality(self, event: Dict) -> Tuple[bool, Dict[str, Any]]:
        """
        Valida calidad de mercado: liquidez, spread, volumen.

        Returns:
            (is_valid, quality_report)
        """
        markets = event.get("markets") or []

        if not markets:
            return False, {"reason": "No markets found"}

        market = markets[0]

        # Verificar volumen/liquidez
        volume = market.get("volume", 0)
        if volume < self.min_liquidity:
            return False, {
                "reason": "Insufficient liquidity",
                "volume": volume,
                "required": self.min_liquidity
            }

        # Verificar spread (si está disponible)
        orders = market.get("orders", {})
        if orders:
            best_bid = orders.get("bestBid", {}).get("price", 0)
            best_ask = orders.get("bestAsk", {}).get("price", 0)

            if best_bid > 0 and best_ask > 0:
                spread_pct = (best_ask - best_bid) / best_bid * 100
                if spread_pct > self.max_spread_pct:
                    return False, {
                        "reason": "Spread too wide",
                        "spread_pct": spread_pct,
                        "max_allowed": self.max_spread_pct
                    }

        # Verificar que el mercado esté activo
        if market.get("active") is False:
            return False, {"reason": "Market not active"}

        return True, {
            "volume": volume,
            "status": "market_valid"
        }

    def score_market(self, event: Dict, now: int) -> float:
        """
        Asigna un score a un mercado basado en múltiples factores.
        Score más alto = mejor mercado para trading.

        Factores:
        - Cercanía al cierre (preferimos mercados que cierran pronto)
        - Liquidez (preferimos mercados con más volumen)
        - Tamaño del spread (preferimos spreads más pequeños)
        """
        markets = event.get("markets") or []
        if not markets:
            return 0.0

        market = markets[0]
        slug = (event.get("slug") or "")

        # 1. Tiempo hasta cierre (preferimos mercados cercanos)
        end_epoch = self.parse_epoch_from_slug(slug)
        if not end_epoch or end_epoch <= now:
            return 0.0

        time_to_close = end_epoch - now
        time_score = 1.0 / (1.0 + time_to_close / 3600)  # Decae con horas hasta cierre

        # 2. Liquidez (preferimos más volumen)
        volume = market.get("volume", 0)
        liquidity_score = min(volume / 10000, 1.0)  # Normaliza a 0-1

        # 3. Spread (preferimos spreads más pequeños)
        orders = market.get("orders", {})
        spread_score = 1.0  # Default si no hay datos de spread
        if orders:
            best_bid = orders.get("bestBid", {}).get("price", 0)
            best_ask = orders.get("bestAsk", {}).get("price", 0)
            if best_bid > 0 and best_ask > 0:
                spread_pct = (best_ask - best_bid) / best_bid * 100
                spread_score = max(0, 1.0 - spread_pct / 10.0)  # Penaliza spreads > 10%

        # Score compuesto (pesos ajustables)
        total_score = (0.4 * time_score + 0.4 * liquidity_score + 0.2 * spread_score)

        return total_score

    def select_best_market(self) -> Optional[Dict]:
        """
        Selecciona el mejor mercado disponible basado en scoring.

        Returns:
            Diccionario con información del mercado seleccionado o None
        """
        now = int(time.time())
        best_market = None
        best_score = 0.0

        for page in range(0, 50):  # hasta 5000 eventos
            events = self.fetch_events(limit=100, offset=page * 100)
            if not events:
                break

            for event in events:
                # Verificar criterios básicos
                if not self.is_candidate(event):
                    continue

                slug = event.get("slug", "")
                end_epoch = self.parse_epoch_from_slug(slug)

                # Verificar que no haya expirado
                if not end_epoch or end_epoch <= now:
                    continue

                # Validar calidad de mercado
                is_valid, quality_report = self.validate_market_quality(event)
                if not is_valid:
                    continue

                # Calcular score
                score = self.score_market(event, now)

                if score > best_score:
                    markets = event.get("markets") or []
                    market_id = markets[0].get("id") if markets else None

                    best_market = {
                        "event_id": event.get("id"),
                        "market_id": market_id,
                        "slug": slug,
                        "end_epoch": end_epoch,
                        "end_utc": datetime.fromtimestamp(end_epoch, tz=timezone.utc).isoformat(),
                        "score": score,
                        "quality_report": quality_report
                    }
                    best_score = score

        # Guardar en historial
        if best_market:
            best_market["selected_at"] = datetime.now(timezone.utc).isoformat()
            self.selection_history.append(best_market)

        return best_market

    def get_selection_stats(self) -> Dict[str, Any]:
        """
        Retorna estadísticas de selecciones recientes.
        """
        if not self.selection_history:
            return {
                "total_selections": 0,
                "last_selection": None,
                "average_score": 0.0
            }

        total = len(self.selection_history)
        avg_score = sum(m["score"] for m in self.selection_history) / total

        return {
            "total_selections": total,
            "last_selection": self.selection_history[-1] if self.selection_history else None,
            "average_score": avg_score,
            "best_score": max(m["score"] for m in self.selection_history),
            "worst_score": min(m["score"] for m in self.selection_history)
        }