from flask import Blueprint, jsonify, request
from app.db import get_db, get_setting, set_setting
from datetime import datetime

trading_bp = Blueprint('trading_bp', __name__)

def _normalize_position_payload(data):
    payload = data or {}
    symbol = str(payload.get('symbol') or '').strip().upper()
    name = str(payload.get('name') or '').strip()
    quantity = int(payload.get('quantity') or 0)
    avg_price = float(payload.get('avg_price') or 0.0)
    current_price = float(payload.get('current_price') or 0.0)
    market_value = float(payload.get('market_value') or 0.0)
    profit_loss = float(payload.get('profit_loss') or 0.0)
    profit_loss_pct = float(payload.get('profit_loss_pct') or 0.0)

    if not symbol:
        raise ValueError('股票代码不能为空')
    if not name:
        raise ValueError('股票名称不能为空')
    if quantity <= 0:
        raise ValueError('持仓数量必须大于0')
    if quantity % 100 != 0:
        raise ValueError('持仓数量必须是100股的整数倍')
    if avg_price <= 0 or current_price <= 0:
        raise ValueError('价格必须大于0')

    return (
        symbol,
        name,
        quantity,
        avg_price,
        current_price,
        market_value,
        profit_loss,
        profit_loss_pct
    )

@trading_bp.route('/api/positions', methods=['GET', 'POST'])
def handle_positions():
    try:
        db = get_db()
        if request.method == 'GET':
            positions = db.execute('SELECT * FROM positions ORDER BY created_at DESC').fetchall()
            result = [dict(pos) for pos in positions]
            return jsonify(result)
        
        elif request.method == 'POST':
            data = request.json
            position = _normalize_position_payload(data)
            cursor = db.execute('''
                INSERT INTO positions (symbol, name, quantity, avg_price, current_price, market_value, profit_loss, profit_loss_pct)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', position)
            db.commit()
            return jsonify({'success': True, 'id': cursor.lastrowid, 'message': '持仓已添加'})
    except ValueError as e:
        return jsonify({'error': str(e), 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e), 'message': '处理持仓请求失败'}), 500

@trading_bp.route('/api/positions/<int:position_id>', methods=['PUT', 'DELETE'])
def handle_position(position_id):
    try:
        db = get_db()
        if request.method == 'PUT':
            data = request.json
            position = _normalize_position_payload(data)
            db.execute('''
                UPDATE positions 
                SET symbol=?, name=?, quantity=?, avg_price=?, current_price=?, 
                    market_value=?, profit_loss=?, profit_loss_pct=?, updated_at=?
                WHERE id=?
            ''', position + (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), position_id))
            db.commit()
            return jsonify({'success': True, 'message': '持仓已更新'})
        
        elif request.method == 'DELETE':
            db.execute('DELETE FROM positions WHERE id = ?', (position_id,))
            db.commit()
            return jsonify({'success': True, 'message': '持仓已删除'})
    except ValueError as e:
        return jsonify({'error': str(e), 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e), 'message': '处理持仓操作失败'}), 500

@trading_bp.route('/api/trades', methods=['GET', 'POST'])
def handle_trades():
    try:
        db = get_db()
        if request.method == 'GET':
            symbol_filter = request.args.get('symbol')
            query = 'SELECT * FROM trade_records ORDER BY trade_time DESC'
            params = []
            if symbol_filter and symbol_filter != '全部':
                query = 'SELECT * FROM trade_records WHERE symbol = ? ORDER BY trade_time DESC'
                params = [symbol_filter]
            
            trades = db.execute(query, params).fetchall()
            return jsonify([dict(t) for t in trades])
        
        elif request.method == 'POST':
            data = request.json or {}
            symbol = str(data.get('symbol') or '').strip().upper()
            direction = str(data.get('direction') or '').strip()
            if not symbol:
                return jsonify({'error': '股票代码不能为空'}), 400
            if direction not in ('买入', '卖出', 'buy', 'sell'):
                return jsonify({'error': "direction 必须为 '买入'/'卖出'/'buy'/'sell'"}), 400
            try:
                price = float(data['price'])
                quantity = int(data['quantity'])
                amount = float(data['amount'])
                fee = float(data.get('fee') or 0.0)
            except (KeyError, TypeError, ValueError) as exc:
                return jsonify({'error': f'字段类型错误: {exc}'}), 400
            if price <= 0:
                return jsonify({'error': '价格必须大于0'}), 400
            if quantity <= 0:
                return jsonify({'error': '数量必须大于0'}), 400
            db.execute('''
                INSERT INTO trade_records (symbol, direction, price, quantity, amount, fee)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (symbol, direction, price, quantity, amount, fee))
            db.commit()
            return jsonify({'success': True, 'message': '交易记录已添加'})
    except Exception as e:
        return jsonify({'error': str(e), 'message': '处理交易记录请求失败'}), 500

@trading_bp.route('/api/funds', methods=['GET', 'POST'])
def handle_funds():
    try:
        if request.method == 'GET':
            available_funds = get_setting('available_funds', '100000.0')
            return jsonify({'available_funds': float(available_funds)})
        
        elif request.method == 'POST':
            data = request.json
            funds = data.get('available_funds', 100000.0)
            set_setting('available_funds', funds)
            return jsonify({'success': True, 'message': '资金已更新'})
    except Exception as e:
        return jsonify({'error': str(e), 'message': '处理资金请求失败'}), 500

@trading_bp.route('/api/strategy/status', methods=['GET', 'POST'])
def handle_strategy_status():
    try:
        db = get_db()
        if request.method == 'GET':
            status = db.execute('SELECT * FROM strategy_status ORDER BY id DESC LIMIT 1').fetchone()
            if status:
                return jsonify(dict(status))
            else:
                return jsonify({
                    'is_running': False,
                    'active_positions': 0,
                    'daily_pnl': 0.0,
                    'total_pnl': 0.0,
                    'signals_today': 0,
                    'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
        
        elif request.method == 'POST':
            data = request.json
            db.execute('''
                INSERT INTO strategy_status (is_running, active_positions, daily_pnl, total_pnl, signals_today)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                1 if data.get('is_running') else 0,
                data.get('active_positions', 0),
                data.get('daily_pnl', 0.0),
                data.get('total_pnl', 0.0),
                data.get('signals_today', 0)
            ))
            db.commit()
            return jsonify({'success': True, 'message': '策略状态已更新'})
    except Exception as e:
        return jsonify({'error': str(e), 'message': '处理策略状态请求失败'}), 500
