# ⚡ Instrucciones de Setup y Ejecución

## 1. Instalación de Dependencias

### Opción A: Usando pip (Recomendada)
```bash
# Navegar al proyecto
cd /ruta/a/jesus-polyclaw

# Instalar dependencias
pip install -r requirements.txt

# O alternativamente con pip3
pip3 install -r requirements.txt
```

### Opción B: Usando venv (Entorno virtual)
```bash
# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
# En Linux/Mac:
source venv/bin/activate
# En Windows:
# venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Para salir del entorno virtual después:
# deactivate
```

## 2. Verificar Instalación

```bash
# Verificar que ccxt está instalado
python3 -c "import ccxt; print('✅ ccxt:', ccxt.__version__)"

# Verificar que ta está instalado
python3 -c "import ta; print('✅ ta:', ta.__version__)"

# Verificar todas las dependencias
python3 -c "
import ccxt, ta, pandas, numpy, scipy, requests
print('✅ Todas las dependencias instaladas correctamente')
"
```

## 3. Ejecutar el Daemon de Paper Trading

### Opción A: En primer plano (para ver logs en tiempo real)
```bash
cd /ruta/a/jesus-polyclaw
python3 src/paper_trading_daemon.py --duration 2 --strategy combined
```

### Opción B: En background (ejecución continua)
```bash
# Crear directorio de logs
mkdir -p logs

# Ejecutar en background con logs
nohup python3 src/paper_trading_daemon.py --duration 2 --strategy combined > logs/daemon.log 2>&1 &

# Verificar que está corriendo
ps aux | grep paper_trading_daemon

# Ver logs en tiempo real
tail -f logs/daemon.log
```

### Opción C: Usando scripts de ayuda
```bash
# Verificar estado del daemon
./check_status.sh

# Ver reporte completo
./monitor_daemon.sh
```

## 4. Parar el Daemon

```bash
# Detener daemon
pkill -f paper_trading_daemon.py

# Verificar que se detuvo
ps aux | grep paper_trading_daemon
```

## 5. Estrategias Disponibles

- `baseline`: Baseline mejorada (momentum + rango)
- `rsi`: RSI con Bollinger Bands
- `combined`: Consenso de múltiples indicadores (default)
- `adaptive_rsi`: RSI adaptativo según volatilidad

Ejemplo:
```bash
python3 src/paper_trading_daemon.py --duration 2 --strategy rsi
```

## 6. Ver Reporte Final

Cuando termine el daemon (o lo detengas), se generarán:

- `paper_trading_report.json` - Reporte principal
- `paper_trading_logs.json` - Logs estructurados
- `paper_trading_status.json` - Estado del monitor
- `paper_trading_alerts.json` - Alertas generadas

Para ver el reporte:
```bash
cat paper_trading_report.json

# O formateado con jq si lo tienes instalado
jq . paper_trading_report.json
```

## 7. Ejecutar Tests (Opcional)

```bash
# Instalar pytest si no lo tienes
pip install pytest

# Ejecutar todos los tests
pytest tests/

# Ejecutar tests con output detallado
pytest tests/ -v

# Ejecutar tests específicos
pytest tests/test_strategies.py -v
```

## 8. Troubleshooting

### Error: `ModuleNotFoundError: No module named 'ccxt'`
```bash
# Solución: Instalar dependencias
pip install -r requirements.txt
```

### Error: `Permission denied` al escribir logs
```bash
# Solución: Crear directorio de logs con permisos
mkdir -p logs
chmod 755 logs
```

### Error: Daemon no arranca
```bash
# Verificar logs
cat logs/daemon.log

# Reinstalar dependencias
pip install -r requirements.txt --force-reinstall
```

### Daemon consume mucho CPU
```bash
# Verificar uso de recursos
top -p $(pgrep -f paper_trading_daemon)

# El daemon hace peticiones cada 5 minutos, consumo debe ser bajo
```

---

## ✅ Checklist Antes de Empezar

- [ ] Python 3.10+ instalado
- [ ] pip disponible
- [ ] Dependencias instaladas (`pip install -r requirements.txt`)
- [ ] Directorio de logs creado (`mkdir -p logs`)
- [ ] Estrategia seleccionada (default: combined)
- [ ] Duración configurada (default: 2 horas)

## 📊 Después de Ejecutar

1. Revisar `paper_trading_report.json` para métricas principales
2. Revisar `logs/daemon.log` para detalles de ejecución
3. Analizar `paper_trading_alerts.json` para alertas de riesgo
4. Comparar resultados con diferentes estrategias
5. Ajustar parámetros en `config/trading_config.py` si es necesario

---

**¡Listo para paper trading! 🚀**