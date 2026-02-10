#!/bin/bash
# Script para monitorear el daemon de paper trading

echo "🔍 MONITOREO DEL DAEMON DE PAPER TRADING"
echo "========================================"
echo ""

# Verificar si el proceso está corriendo
if pgrep -f "paper_trading_daemon.py" > /dev/null; then
    echo "✅ Estado: RUNNING (daemon activo)"
    echo ""
else
    echo "❌ Estado: STOPPED (daemon no encontrado)"
    echo ""
fi

# Verificar el archivo de log
if [ -f "logs/daemon.log" ]; then
    echo "📄 Últimas líneas del log:"
    echo "------------------------"
    tail -20 logs/daemon.log
    echo ""
fi

# Verificar si hay reportes generados
if [ -f "paper_trading_report.json" ]; then
    echo "📊 REPORT FINAL GENERADO:"
    echo "-------------------------"
    cat paper_trading_report.json
else
    echo "⏳ El daemon aún no ha generado el reporte final"
    echo ""
fi

echo ""
echo "🔍 Para ver el log en tiempo real:"
echo "   tail -f logs/daemon.log"
echo ""
echo "🔍 Para detener el daemon:"
echo "   pkill -f paper_trading_daemon.py"
echo ""