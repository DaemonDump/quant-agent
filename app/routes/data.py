import tushare as ts
from flask import Blueprint, jsonify, request, current_app
from data_ingestion import RealTimeDataCollector, add_monitored_symbol, remove_monitored_symbol, get_monitored_symbols
from app.db import get_setting, set_setting
from datetime import datetime, timedelta
import time

data_bp = Blueprint('data_bp', __name__)

# 简单内存缓存
_cache = {
    'stock_basic': {'data': None, 'expire_at': 0},
    'indices': {'data': None, 'expire_at': 0},
    'indices_history': {'data': None, 'expire_at': 0},
    'quotes': {'data': None, 'expire_at': 0, 'key': ''}
}

@data_bp.route('/api/settings/token', methods=['GET', 'POST', 'DELETE'])
def handle_token():
    try:
        if request.method == 'GET':
            token = get_setting('tushare_token', '')
            return jsonify({'has_token': bool(token)})
        
        elif request.method == 'POST':
            data = request.json
            token = data.get('token', '').strip()
            if token:
                set_setting('tushare_token', token)
                return jsonify({'success': True, 'message': 'Token已保存'})
            else:
                return jsonify({'success': False, 'message': 'Token不能为空'})
        
        elif request.method == 'DELETE':
            set_setting('tushare_token', '')
            return jsonify({'success': True, 'message': 'Token已清除'})
    except Exception as e:
        return jsonify({'error': str(e), 'message': '处理Token请求失败'}), 500

@data_bp.route('/api/market/search')
def search_stocks():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify([])
    
    token = get_setting('tushare_token', None)
    if not token:
        return jsonify({'error': 'Token未设置', 'message': '请先设置Tushare API Token'})
    
    try:
        now = time.time()
        if _cache['stock_basic']['data'] is not None and _cache['stock_basic']['expire_at'] > now:
            df = _cache['stock_basic']['data']
        else:
            ts.set_token = lambda x: None
            pro = ts.pro_api(token)
            df = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date')
            _cache['stock_basic']['data'] = df
            _cache['stock_basic']['expire_at'] = now + 86400  # 缓存 24 小时
        
        # 在结果中过滤匹配的代码或名称
        mask = (df['symbol'].str.contains(query, regex=False, na=False) |
                df['name'].str.contains(query, regex=False, na=False))
        results = df[mask].head(10).to_dict('records')
        
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e), 'message': '搜索股票失败'})

@data_bp.route('/api/market/indices')
def market_indices():
    token = get_setting('tushare_token', None)
    if not token:
        return jsonify({'error': 'Token未设置', 'message': '请先设置Tushare API Token'})
    
    try:
        now = time.time()
        force_refresh = str(request.args.get('force', '')).lower() in ('1', 'true', 'yes')
        if (not force_refresh) and _cache['indices']['data'] is not None and _cache['indices']['expire_at'] > now:
            cached = dict(_cache['indices']['data'])
            cached['source'] = 'cache'
            return jsonify(cached)

        # 强制将 tushare 的 set_token 设为空函数，彻底避免权限问题导致的本地文件写入尝试
        ts.set_token = lambda x: None
        pro = ts.pro_api(token)
        
        today = datetime.now()
        for i in range(10):
            test_date = (today - timedelta(days=i)).strftime('%Y%m%d')
            df_hs300 = pro.index_daily(ts_code='000300.SH', start_date=test_date, end_date=test_date)
            df_sh = pro.index_daily(ts_code='000001.SH', start_date=test_date, end_date=test_date)
            df_sz = pro.index_daily(ts_code='399001.SZ', start_date=test_date, end_date=test_date)
            
            if len(df_hs300) > 0 and len(df_sh) > 0 and len(df_sz) > 0:
                result = {
                    'hs300': float(df_hs300['close'].iloc[-1]),
                    'hs300_change': float(df_hs300['pct_chg'].iloc[-1]),
                    'sh': float(df_sh['close'].iloc[-1]),
                    'sh_change': float(df_sh['pct_chg'].iloc[-1]),
                    'sz': float(df_sz['close'].iloc[-1]),
                    'sz_change': float(df_sz['pct_chg'].iloc[-1]),
                    'date': test_date,
                    'source': 'live'
                }
                _cache['indices']['data'] = result
                _cache['indices']['expire_at'] = now + 300  # 缓存 5 分钟
                return jsonify(result)
        
        return jsonify({'error': '无数据', 'message': '最近10天无交易数据'})
    except Exception as e:
        return jsonify({'error': 'API调用失败', 'message': f'获取市场数据失败: {str(e)}'})

@data_bp.route('/api/market/indices/history')
def market_indices_history():
    token = get_setting('tushare_token', None)
    if not token:
        return jsonify({'error': 'Token未设置', 'message': '请先设置Tushare API Token'})

    try:
        now = time.time()
        force_refresh = str(request.args.get('force', '')).lower() in ('1', 'true', 'yes')
        if (not force_refresh) and _cache['indices_history']['data'] is not None and _cache['indices_history']['expire_at'] > now:
            cached = dict(_cache['indices_history']['data'])
            cached['source'] = 'cache'
            return jsonify(cached)

        ts.set_token = lambda x: None
        pro = ts.pro_api(token)

        days = int(request.args.get('days') or 180)
        points = int(request.args.get('points') or 120)
        days = max(30, min(1000, days))
        points = max(30, min(500, points))

        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

        def _fetch(ts_code: str):
            df = pro.index_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            if df is None or df.empty:
                return {'dates': [], 'close': []}
            df = df.sort_values('trade_date')
            if len(df) > points:
                df = df.iloc[-points:]
            return {
                'dates': df['trade_date'].astype(str).tolist(),
                'close': df['close'].astype(float).tolist()
            }

        series = {
            'hs300': _fetch('000300.SH'),
            'sh': _fetch('000001.SH'),
            'sz': _fetch('399001.SZ')
        }
        result = {'series': series, 'start_date': start_date, 'end_date': end_date, 'source': 'live'}
        _cache['indices_history']['data'] = result
        _cache['indices_history']['expire_at'] = now + 300
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': 'API调用失败', 'message': f'获取指数历史失败: {str(e)}'})

@data_bp.route('/api/market/quotes')
def market_quotes():
    token = get_setting('tushare_token', None)
    if not token:
        return jsonify({'error': 'Token未设置', 'message': '请先设置Tushare API Token'})

    symbols_raw = (request.args.get('symbols') or '').strip()
    if not symbols_raw:
        return jsonify({'error': '参数错误', 'message': '缺少symbols参数'}), 400

    symbols = []
    for s in symbols_raw.split(','):
        s = (s or '').strip().upper()
        if s:
            symbols.append(s)
    symbols = list(dict.fromkeys(symbols))
    if not symbols:
        return jsonify({'error': '参数错误', 'message': 'symbols为空'}), 400
    if len(symbols) > 50:
        return jsonify({'error': '参数错误', 'message': 'symbols数量过多(<=50)'}), 400

    try:
        now = time.time()
        force_refresh = str(request.args.get('force', '')).lower() in ('1', 'true', 'yes')
        cache_key = ','.join(symbols)
        if (not force_refresh) and _cache['quotes']['data'] is not None and _cache['quotes']['expire_at'] > now and _cache['quotes'].get('key') == cache_key:
            cached = dict(_cache['quotes']['data'])
            cached['source'] = 'cache'
            return jsonify(cached)

        ts.set_token = lambda x: None
        pro = ts.pro_api(token)

        today = datetime.now()
        chosen_date = ''
        quotes = {s: None for s in symbols}

        for i in range(10):
            test_date = (today - timedelta(days=i)).strftime('%Y%m%d')
            any_found = False
            for s in symbols:
                if quotes.get(s) is not None:
                    continue
                df = pro.daily(ts_code=s, start_date=test_date, end_date=test_date)
                if df is None or df.empty:
                    continue
                row = df.iloc[-1]
                try:
                    quotes[s] = {
                        'price': float(row.get('close')),
                        'pct_chg': float(row.get('pct_chg')) if row.get('pct_chg') is not None else 0.0,
                        'open': float(row.get('open')) if row.get('open') is not None else None,
                        'high': float(row.get('high')) if row.get('high') is not None else None,
                        'low': float(row.get('low')) if row.get('low') is not None else None,
                        'pre_close': float(row.get('pre_close')) if row.get('pre_close') is not None else None,
                        'trade_date': str(row.get('trade_date') or test_date)
                    }
                    any_found = True
                except Exception:
                    continue
            if any_found:
                chosen_date = test_date
                break

        result = {
            'date': chosen_date,
            'quotes': quotes,
            'source': 'live'
        }
        _cache['quotes']['data'] = result
        _cache['quotes']['expire_at'] = now + 60
        _cache['quotes']['key'] = cache_key
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': 'API调用失败', 'message': f'获取行情失败: {str(e)}'})

@data_bp.route('/api/data/symbols', methods=['GET', 'POST'])
def handle_data_symbols():
    try:
        if request.method == 'GET':
            symbols = get_monitored_symbols(current_app.config['DATABASE'])
            return jsonify({'symbols': symbols})
        
        elif request.method == 'POST':
            data = request.json
            action = data.get('action', 'add')
            symbol = data.get('symbol')
            symbol_name = data.get('name', symbol)
            
            if action == 'add':
                success = add_monitored_symbol(current_app.config['DATABASE'], symbol, symbol_name)
                if success:
                    return jsonify({'success': True, 'message': f'已添加监控标的: {symbol}'})
                else:
                    return jsonify({'success': False, 'message': '添加失败'})
            
            elif action == 'remove':
                success = remove_monitored_symbol(current_app.config['DATABASE'], symbol)
                if success:
                    return jsonify({'success': True, 'message': f'已移除监控标的: {symbol}'})
                else:
                    return jsonify({'success': False, 'message': '移除失败'})
            
            else:
                return jsonify({'success': False, 'message': '无效的操作'})
    except Exception as e:
        return jsonify({'error': str(e), 'message': '处理标的请求失败'}), 500

@data_bp.route('/api/data/realtime')
def get_realtime_data():
    try:
        symbol = request.args.get('symbol')
        limit = int(request.args.get('limit', 10))
        
        if not symbol:
            return jsonify({'error': '参数错误', 'message': '缺少symbol参数'}), 400
        
        collector = RealTimeDataCollector(current_app.config['DATABASE'])
        df = collector.get_realtime_data(symbol, limit)
        
        if df.empty:
            return jsonify({'symbol': symbol, 'data': [], 'message': '无数据'})
        
        return jsonify({
            'symbol': symbol,
            'data': df.to_dict('records'),
            'count': len(df)
        })
    except Exception as e:
        return jsonify({'error': str(e), 'message': '获取实时数据失败'}), 500

@data_bp.route('/api/data/history')
def get_history_data():
    try:
        symbol = request.args.get('symbol')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not symbol or not start_date or not end_date:
            return jsonify({'error': '参数错误', 'message': '缺少必要参数'}), 400
        
        collector = RealTimeDataCollector(current_app.config['DATABASE'])
        df = collector.get_history_data(symbol, start_date, end_date)
        
        if df.empty:
            return jsonify({'symbol': symbol, 'data': [], 'message': '无数据'})
        
        return jsonify({
            'symbol': symbol,
            'data': df.to_dict('records'),
            'count': len(df)
        })
    except Exception as e:
        return jsonify({'error': str(e), 'message': '获取历史数据失败'}), 500

@data_bp.route('/api/data/collect', methods=['POST'])
def collect_data():
    try:
        data = request.json
        token = data.get('token') # Assuming token is passed in request
        
        if not token:
            return jsonify({'error': 'Token未设置', 'message': '请先设置Tushare API Token'}), 400
        
        collector = RealTimeDataCollector(current_app.config['DATABASE'])
        collector.set_token(token)
        
        if data.get('symbols'):
            collector.set_symbols(data['symbols'])
        else:
            symbols = get_monitored_symbols(current_app.config['DATABASE'])
            collector.set_symbols([s['symbol'] for s in symbols])
        
        results = collector.collect_realtime_data()
        
        return jsonify({
            'success': True,
            'collected': len(results),
            'symbols': list(results.keys()),
            'message': f'成功采集{len(results)}个标的数据'
        })
    except Exception as e:
        return jsonify({'error': str(e), 'message': '采集数据失败'}), 500

@data_bp.route('/api/data/collect_history', methods=['POST'])
def collect_history_data():
    try:
        data = request.json
        token = data.get('token')
        symbol = data.get('symbol')
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        if not token or not symbol or not start_date or not end_date:
            return jsonify({'error': '参数错误', 'message': '缺少必要参数'}), 400

        collector = RealTimeDataCollector(current_app.config['DATABASE'])
        collector.set_token(token)
        df = collector.collect_history_data(symbol, start_date, end_date)

        if df is not None:
            return jsonify({'success': True, 'message': f'成功采集{symbol}的历史数据'})
        else:
            return jsonify({'success': False, 'message': f'采集{symbol}的历史数据失败'})

    except Exception as e:
        return jsonify({'error': str(e), 'message': '采集历史数据失败'}), 500

@data_bp.route('/api/data/validate/<symbol>')
def validate_data(symbol):
    try:
        collector = RealTimeDataCollector(current_app.config['DATABASE'])
        result = collector.validate_data(symbol)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e), 'message': '验证数据失败'}), 500
