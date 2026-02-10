# Polyclaw-Jesus 🎯

Sistema de trading mejorado para mercados de criptomonedas en Polymarket, con enfoque en gestión de riesgo robusta y backtesting avanzado.

## 🚀 Características Principales

### Infraestructura Mejorada

- **Configuración Centralizada**: Todos los parámetros en un solo archivo para fácil optimización
- **Logging Estructurado**: Tracking detallado de decisiones, trades y errores con exportación JSON
- **Validación de Datos Robusta**: Detección de outliers, validación de relaciones OHLC y limpieza automática
- **Gestión de Riesgo Completa**: Stop-loss/take-profit automáticos, control de exposición y drawdown
- **Monitoreo en Tiempo Real**: Alertas automáticas y reportes detallados del estado del sistema

### Selección de Mercados Inteligente

- Scoring multi-factor (liquidez, spread, tiempo hasta cierre)
- Validación de calidad de mercado
- Historial y estadísticas de selecciones

### Estrategias de Trading

- **Baseline Strategy**: Estrategia mejorada basada en momentum y posición en rango
- **RSI Strategy**: Reversión a la media con confirmación de Bollinger Bands
- **Combined Strategy**: Consenso de múltiples indicadores (RSI, MACD, Momentum)
- **Adaptive RSI Strategy**: RSI con thresholds ajustados según volatilidad

## 📦 Instalación

```bash
cd polyclaw-jesus
pip install -r requirements.txt
```

## 🎮 Uso

### Backtesting

Ejecuta backtesting de estrategias:

```bash
# Testear todas las estrategias
python src/cli.py backtest

# Testear estrategia específica
python src/cli.py backtest --strategy rsi --timeframe 15m --days 14

# Estrategias disponibles: baseline, rsi, combined, adaptive_rsi
```

### Selección de Mercados

Selecciona el mejor mercado actual:

```bash
python src/cli.py select-market --assets btc,eth --timeframes 15m,30m
```

### Paper Trading

Simula trading sin riesgo real:

```bash
python src/cli.py paper-trading --strategy combined --balance 1000
```

## 📊 Métricas de Backtesting

El framework de backtesting proporciona:

- **Balance final y PnL total**
- **Win Rate**: Porcentaje de trades ganadores
- **Max Drawdown**: Pérdida máxima desde el peak
- **Sharpe Ratio**: Riesgo ajustado por retorno
- **Profit Factor**: Ratio de ganancias brutas vs pérdidas brutas
- **Promedio de PnL por trade**

## 🏗️ Arquitectura

```
polyclaw-jesus/
├── config/
│   └── trading_config.py      # Configuración centralizada
├── src/
│   ├── data/
│   │   ├── oracle_prices.py   # Feed de precios OHLCV
│   │   ├── features.py        # Features técnicas
│   │   ├── data_validator.py  # Validación de datos
│   │   └── enhanced_market_selector.py  # Selector de mercados
│   ├── strategy/
│   │   ├── baseline_strategy.py
│   │   ├── rsi_strategy.py
│   │   └── combined_strategy.py
│   ├── risk/
│   │   └── risk_manager.py    # Gestión de riesgo
│   ├── execution/
│   │   └── enhanced_backtest.py  # Framework de backtesting
│   ├── monitoring/
│   │   └── real_time_monitor.py  # Monitoreo en tiempo real
│   ├── utils/
│   │   └── logger.py          # Sistema de logging
│   └── cli.py                 # CLI principal
├── tests/
│   ├── test_data_validator.py
│   └── test_strategies.py
├── docs/
│   └── FINAL_REPORT.md        # Informe final detallado
└── requirements.txt
```

## ⚙️ Configuración

Edita `config/trading_config.py` para ajustar:

- Activos y timeframes
- Parámetros de riesgo (stop-loss, take-profit, exposición máxima)
- Límites de drawdown y pérdida diaria
- Configuración de logging y monitoreo

## 🧪 Testing

Ejecuta tests:

```bash
pytest tests/
```

## 📝 Comparación con Polyclaw Original

### Mejoras Implementadas

1. **Validación de Datos**: Detección de outliers y datos corruptos
2. **Gestión de Riesgo**: Sistema completo con múltiples niveles de control
3. **Monitoreo**: Alertas automáticas y tracking en tiempo real
4. **Logging**: Estructurado y exportable para análisis
5. **Estrategias**: Más robustas y con múltiples confirmaciones
6. **CLI**: Interfaz unificada para todas las operaciones

### Puntos Fuertes Mantenidos

- Feed de oracles de ccxt
- Cálculo de features técnicas con `ta`
- Framework de backtesting A/B
- Filtrado de mercados por patrones de nomenclatura

## 🔮 Próximos Pasos

### Infraestructura Recomendada

Para producción y baja latencia:

- **Chainstack**: Infraestructura de blockchain optimizada para baja latencia
- **Redis**: Caching de datos de mercado para sub-millisecond responses
- **Prometheus + Grafana**: Monitoreo y alertas en tiempo real
- **PostgreSQL**: Almacenamiento persistente de trades y métricas

### Consideraciones de Deployment

- Dockerizado para deployment consistente
- Separación de entornos (dev/test/prod)
- Configuración de rate limits para APIs externas
- Implementación de circuit breakers para failover

## 📄 Licencia

Este proyecto es un fork mejorado de Polyclaw, manteniendo el mismo enfoque en research sandbox para mercados tipo Polymarket.

## 👥 Contribuciones

Este proyecto está en fase de desarrollo activo. Para contribuir, revisa el archivo `docs/FINAL_REPORT.md` para entender el estado actual y áreas de mejora.

---

**Estado**: Research phase / Paper trading enabled. No live trading activado.