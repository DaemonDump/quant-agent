from flask import Blueprint, jsonify, request
from live_ops import RealtimeMonitor, TradeLogger, IterationOptimizer, EmergencyHandler

monitor_bp = Blueprint('monitor_bp', __name__)
_emergency_handler = EmergencyHandler()
_trade_logger = TradeLogger()
_realtime_monitor = RealtimeMonitor()

@monitor_bp.route('/api/monitor/status', methods=['GET'])
def get_monitor_status():
    try:
        status = _realtime_monitor.get_status()
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        return jsonify({'error': str(e), 'message': '获取监控状态失败'}), 500

@monitor_bp.route('/api/monitor/performance', methods=['GET'])
def get_monitor_performance():
    try:
        limit = request.args.get('limit', 100, type=int)
        performance = _realtime_monitor.get_performance_history(limit)
        return jsonify({
            'success': True,
            'performance': performance
        })
    except Exception as e:
        return jsonify({'error': str(e), 'message': '获取绩效历史失败'}), 500

@monitor_bp.route('/api/monitor/anomalies', methods=['GET'])
def get_monitor_anomalies():
    try:
        limit = request.args.get('limit', 100, type=int)
        anomalies = _realtime_monitor.get_anomaly_history(limit)
        return jsonify({
            'success': True,
            'anomalies': anomalies
        })
    except Exception as e:
        return jsonify({'error': str(e), 'message': '获取异常历史失败'}), 500

@monitor_bp.route('/api/logger/trades', methods=['GET'])
def get_trade_log():
    try:
        symbol = request.args.get('symbol')
        limit = request.args.get('limit', 100, type=int)
        trades = _trade_logger.get_trade_log(symbol, limit)
        return jsonify({
            'success': True,
            'trades': trades
        })
    except Exception as e:
        return jsonify({'error': str(e), 'message': '获取交易日志失败'}), 500


@monitor_bp.route('/api/emergency/history', methods=['GET'])
def get_emergency_history():
    try:
        limit = request.args.get('limit', 100, type=int)
        history = _emergency_handler.get_emergency_history(limit)
        return jsonify({'success': True, 'history': history})
    except Exception as e:
        return jsonify({'error': str(e), 'message': '获取紧急历史失败'}), 500


@monitor_bp.route('/api/emergency/summary', methods=['GET'])
def get_emergency_summary():
    try:
        summary = _emergency_handler.get_emergency_summary()
        return jsonify({'success': True, 'summary': summary})
    except Exception as e:
        return jsonify({'error': str(e), 'message': '获取紧急汇总失败'}), 500
