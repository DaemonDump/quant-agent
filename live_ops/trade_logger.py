import pandas as pd
import numpy as np
import sqlite3
import os
from typing import Dict, Any, List
from datetime import datetime, timedelta
from app.utils import logger


def _get_db_connection():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(root, 'data', 'tushare', 'db', 'quant_data.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


class TradeLogger:
    def __init__(self):
        # 绩效和异常日志暂时保留在内存（如需持久化可类似处理）
        self.trade_log = []
        self.performance_log = []
        self.anomaly_log = []
        
        logger.info("交易记录器初始化完成")
    
    def log_trade(self, trade_data: Dict[str, Any]):
        """记录交易"""
        try:
            conn = _get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO trade_records (symbol, direction, price, quantity, amount, fee, trade_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_data.get('symbol', ''),
                trade_data.get('direction', ''),
                float(trade_data.get('price', 0)),
                int(trade_data.get('quantity', 0)),
                float(trade_data.get('amount', 0)),
                float(trade_data.get('fee', 0.0)),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            
            logger.info(f"记录交易到数据库: {trade_data.get('direction')} {trade_data.get('symbol')} {trade_data.get('quantity')}股 @ {trade_data.get('price')}")
        except Exception as e:
            logger.error(f"记录交易失败: {e}")
            
    def get_trade_log(self, symbol: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """获取交易记录"""
        try:
            conn = _get_db_connection()
            cursor = conn.cursor()
            
            if symbol:
                cursor.execute('''
                    SELECT * FROM trade_records 
                    WHERE symbol = ? 
                    ORDER BY trade_time DESC 
                    LIMIT ?
                ''', (symbol, limit))
            else:
                cursor.execute('''
                    SELECT * FROM trade_records 
                    ORDER BY trade_time DESC 
                    LIMIT ?
                ''', (limit,))
                
            rows = cursor.fetchall()
            conn.close()
            
            # 将 sqlite3.Row 转换为字典
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取交易记录失败: {e}")
            return []
    
    def log_performance(self, performance_data: Dict[str, Any]):
        """记录绩效"""
        try:
            performance_record = {
                'timestamp': pd.Timestamp.now().isoformat(),
                'date': datetime.now().strftime('%Y-%m-%d'),
                'total_value': performance_data.get('total_value', 0),
                'total_cost': performance_data.get('total_cost', 0),
                'pnl': performance_data.get('pnl', 0),
                'pnl_pct': performance_data.get('pnl_pct', 0),
                'positions_count': performance_data.get('positions_count', 0),
                'daily_return': performance_data.get('daily_return', 0),
                'max_drawdown': performance_data.get('max_drawdown', 0),
                'sharpe_ratio': performance_data.get('sharpe_ratio', 0)
            }
            
            self.performance_log.append(performance_record)
            
            logger.info(f"记录绩效: 总值¥{performance_record['total_value']:.2f}, 盈亏¥{performance_record['pnl']:.2f} ({performance_record['pnl_pct']:.2f}%)")
            
            if len(self.performance_log) > 10000:
                self.performance_log = self.performance_log[-10000:]
            
        except Exception as e:
            logger.error(f"记录绩效失败: {e}")
    
    def log_anomaly(self, anomaly_data: Dict[str, Any]):
        """记录异常"""
        try:
            anomaly_record = {
                'timestamp': pd.Timestamp.now().isoformat(),
                'type': anomaly_data.get('type', ''),
                'level': anomaly_data.get('level', 'info'),
                'message': anomaly_data.get('message', ''),
                'details': anomaly_data.get('details', ''),
                'resolved': anomaly_data.get('resolved', False)
            }
            
            self.anomaly_log.append(anomaly_record)
            
            logger.warning(f"记录异常: {anomaly_record['type']} - {anomaly_record['message']}")
            
            if len(self.anomaly_log) > 10000:
                self.anomaly_log = self.anomaly_log[-10000:]
            
        except Exception as e:
            logger.error(f"记录异常失败: {e}")
    
    def get_performance_log(self, days: int = 30, limit: int = 100) -> List[Dict[str, Any]]:
        """获取绩效日志"""
        if not self.performance_log:
            return []
        
        cutoff_date = datetime.now() - timedelta(days=days)
        performance = [p for p in self.performance_log if datetime.fromisoformat(p['timestamp']) >= cutoff_date]
        
        return performance[-limit:] if performance else []
    
    def get_anomaly_log(self, level: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """获取异常日志"""
        anomalies = self.anomaly_log
        
        if level:
            anomalies = [a for a in anomalies if a['level'] == level]
        
        return anomalies[-limit:] if anomalies else []
    
    def get_daily_performance(self, date: str = None) -> Dict[str, Any]:
        """获取指定日期的绩效"""
        if not self.performance_log:
            return None
        
        target_date = date or datetime.now().strftime('%Y-%m-%d')
        daily_performance = [p for p in self.performance_log if p['date'] == target_date]
        
        if not daily_performance:
            return None
        
        latest = daily_performance[-1]
        
        return {
            'date': latest['date'],
            'total_value': latest['total_value'],
            'total_cost': latest['total_cost'],
            'pnl': latest['pnl'],
            'pnl_pct': latest['pnl_pct'],
            'positions_count': latest['positions_count'],
            'daily_return': latest['daily_return'],
            'max_drawdown': latest['max_drawdown'],
            'sharpe_ratio': latest['sharpe_ratio']
        }
    
    def get_trade_statistics(self, days: int = 30) -> Dict[str, Any]:
        """获取交易统计"""
        trades = self.get_trade_log(limit=10000)
        
        if not trades:
            return {
                'total_trades': 0,
                'buy_trades': 0,
                'sell_trades': 0,
                'total_amount': 0,
                'avg_amount': 0,
                'success_rate': 0
            }
        
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_trades = []
        for t in trades:
            ts = t.get('trade_time') or t.get('timestamp')
            if not ts:
                continue
            try:
                if datetime.fromisoformat(str(ts)) >= cutoff_date:
                    recent_trades.append(t)
            except Exception:
                continue
        
        buy_trades = [t for t in recent_trades if (t.get('direction') or '').lower() in ('buy', '买入')]
        sell_trades = [t for t in recent_trades if (t.get('direction') or '').lower() in ('sell', '卖出')]
        
        total_amount = sum(float(t.get('amount') or 0) for t in recent_trades)
        avg_amount = total_amount / len(recent_trades) if recent_trades else 0
        success_rate = 100.0 if recent_trades else 0.0
        
        return {
            'period_days': days,
            'total_trades': len(recent_trades),
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades),
            'total_amount': total_amount,
            'avg_amount': avg_amount,
            'success_rate': success_rate
        }
    
    def get_performance_summary(self, days: int = 30) -> Dict[str, Any]:
        """获取绩效汇总"""
        performance = self.get_performance_log(days=days, limit=10000)
        
        if not performance:
            return {
                'period_days': days,
                'total_pnl': 0,
                'avg_daily_pnl': 0,
                'best_day': None,
                'worst_day': None,
                'win_rate': 0,
                'max_drawdown': 0
            }
        
        daily_pnl = [p['pnl'] for p in performance]
        total_pnl = sum(daily_pnl)
        avg_daily_pnl = total_pnl / len(daily_pnl) if daily_pnl else 0
        
        best_day = max(performance, key=lambda x: x['pnl']) if performance else None
        worst_day = min(performance, key=lambda x: x['pnl']) if performance else None
        
        win_days = [p for p in performance if p['pnl'] > 0]
        win_rate = len(win_days) / len(performance) * 100 if performance else 0
        
        max_drawdown = max([p['max_drawdown'] for p in performance]) if performance else 0
        
        return {
            'period_days': days,
            'total_pnl': total_pnl,
            'avg_daily_pnl': avg_daily_pnl,
            'best_day': {
                'date': best_day['date'],
                'pnl': best_day['pnl'],
                'pnl_pct': best_day['pnl_pct']
            } if best_day else None,
            'worst_day': {
                'date': worst_day['date'],
                'pnl': worst_day['pnl'],
                'pnl_pct': worst_day['pnl_pct']
            } if worst_day else None,
            'win_rate': win_rate,
            'max_drawdown': max_drawdown
        }
    
    def clear_old_logs(self, days: int = 90):
        """清理旧日志"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            self.trade_log = [t for t in self.trade_log if datetime.fromisoformat(str(t.get('trade_time') or t.get('timestamp', ''))) >= cutoff_date]
            self.performance_log = [p for p in self.performance_log if datetime.fromisoformat(p['timestamp']) >= cutoff_date]
            self.anomaly_log = [a for a in self.anomaly_log if datetime.fromisoformat(a['timestamp']) >= cutoff_date]
            
            logger.info(f"清理{days}天前的旧日志完成")
            
        except Exception as e:
            logger.error(f"清理旧日志失败: {e}")
    
    def export_logs(self, file_path: str):
        """导出日志到文件"""
        try:
            import json
            
            logs = {
                'trade_log': self.trade_log,
                'performance_log': self.performance_log,
                'anomaly_log': self.anomaly_log,
                'export_time': pd.Timestamp.now().isoformat()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(logs, f, ensure_ascii=False, indent=2)
            
            logger.info(f"日志已导出到: {file_path}")
            
        except Exception as e:
            logger.error(f"导出日志失败: {e}")
