#!/bin/bash
# Script rápido para verificar el estado del daemon

echo "⚡ ESTADO DEL DAEMON"
echo "==================="
echo ""

# Verificar proceso
if pgrep -f "paper_trading_daemon.py" > /dev/null; then
    echo "✅ Daemon: ACTIVO"
else
    echo "❌ Daemon: DETENIDO"
    echo ""
    exit 1
fi

# Mostrar última actividad del log
if [ -f "logs/daemon.log" ]; then
    echo ""
    echo "📊 ÚLTIMA ACTIVIDAD:"
    echo "--------------------"
    tail -5 logs/daemon.log
    echo ""
else
    echo "⚠️  No hay archivo de log"
fi

# Verificar si hay reporte final
if [ -f "paper_trading_report.json" ]; then
    echo "✅ Reporte final disponible: paper_trading_report.json"
fi