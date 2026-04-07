import pandas as pd
import numpy as np
import sqlite3
import os
import time
from typing import Dict, Any, List
from app.utils import logger


def _get_db_connection():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(root, 'data', 'tushare', 'db', 'quant_data.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


class RealtimeMonitor:
    def __init__(self):
        self.is_running = False
        self.positions = {}
        self.monitor_interval = 60  # 监控间隔（秒）
        self.performance_history = []
        self.anomaly_history = []
        
        logger.info("实时监控器初始化完成")
    
    def start_monitoring(self):
        """启动实时监控"""
        self.is_running = True
        logger.info("实时监控已启动")
        
        while self.is_running:
            _start = time.time()
            try:
                self.monitor_trades()
                self.monitor_performance()
                self.monitor_anomalies()
            except Exception as e:
                logger.error(f"监控过程出错: {e}")
                self.record_anomaly("系统异常", str(e))
            _elapsed = time.time() - _start
            _sleep = max(0.0, self.monitor_interval - _elapsed)
            if _sleep > 0:
                time.sleep(_sleep)
        
        logger.info("实时监控已停止")
    
    def stop_monitoring(self):
        """停止实时监控"""
        self.is_running = False
        logger.info("正在停止实时监控...")
    
    def monitor_trades(self):
        """监控交易执行"""
        try:
            conn = _get_db_connection()
            
            query = '''
                SELECT * FROM trade_records
                ORDER BY trade_time DESC
                LIMIT 50
            '''
            pending_trades = pd.read_sql_query(query, conn)
            conn.close()
            
            if not pending_trades.empty:
                logger.info(f"最近交易记录{len(pending_trades)}笔")
            
        except Exception as e:
            logger.error(f"监控交易执行失败: {e}")
    
    def execute_trade(self, trade: pd.Series):
        """执行单笔交易"""
        try:
            logger.info(f"交易记录: {trade.get('direction')} {trade.get('symbol')} {trade.get('quantity')}股 @ {trade.get('price')}")
            
        except Exception as e:
            logger.error(f"执行交易失败: {e}")
    
    def monitor_performance(self):
        """监控绩效"""
        try:
            conn = _get_db_connection()
            
            query = 'SELECT * FROM positions'
            positions_df = pd.read_sql_query(query, conn)
            conn.close()
            
            if positions_df.empty:
                return
            
            total_value = positions_df['market_value'].sum()
            total_cost = (positions_df['avg_price'].fillna(0) * positions_df['quantity'].fillna(0)).sum()
            
            current_pnl = total_value - total_cost
            current_pnl_pct = (current_pnl / total_cost) * 100 if total_cost > 0 else 0
            
            performance = {
                'timestamp': pd.Timestamp.now().isoformat(),
                'total_value': total_value,
                'total_cost': total_cost,
                'pnl': current_pnl,
                'pnl_pct': current_pnl_pct,
                'positions_count': len(positions_df)
            }
            
            self.performance_history.append(performance)
            
            logger.info(f"当前绩效: 总值¥{total_value:.2f}, 盈亏¥{current_pnl:.2f} ({current_pnl_pct:.2f}%)")
            
            if len(self.performance_history) > 1000:
                self.performance_history = self.performance_history[-1000:]
            
        except Exception as e:
            logger.error(f"监控绩效失败: {e}")
    
    def monitor_anomalies(self):
        """监控异常"""
        try:
            conn = _get_db_connection()
            
            query = '''
                SELECT symbol,
                       open_price as open, high_price as high, low_price as low, close_price as close,
                       volume as vol, amount
                FROM stock_history_data
                WHERE trade_date = (
                    SELECT MAX(trade_date) FROM stock_history_data
                )
            '''
            latest_data = pd.read_sql_query(query, conn)
            conn.close()
            
            if latest_data.empty:
                return
            
            anomalies = self._detect_price_anomalies(latest_data)
            anomalies.extend(self._detect_volume_anomalies(latest_data))
            
            for anomaly in anomalies:
                logger.warning(f"检测到异常: {anomaly}")
                self.record_anomaly("数据异常", anomaly)
            
        except Exception as e:
            logger.error(f"监控异常失败: {e}")
    
    def _detect_price_anomalies(self, data: pd.DataFrame) -> List[str]:
        """检测价格异常"""
        anomalies = []
        
        for _, row in data.iterrows():
            if row['high'] > 0 and row['low'] > 0:
                price_change = abs(row['close'] - row['open']) / row['open']
                
                if price_change > 0.2:
                    anomalies.append(f"{row['symbol']} 价格异常波动: {price_change*100:.2f}%")
        
        return anomalies
    
    def _detect_volume_anomalies(self, data: pd.DataFrame) -> List[str]:
        """检测成交量异常"""
        anomalies = []
        
        for _, row in data.iterrows():
            if row['vol'] > 0 and row['amount'] > 0:
                avg_price = row['amount'] / row['vol']
                
                if avg_price > 1000 or avg_price < 0.1:
                    anomalies.append(f"{row['symbol']} 成交量异常: 均价{avg_price:.2f}")
        
        return anomalies
    
    def record_anomaly(self, anomaly_type: str, message: str):
        """记录异常"""
        anomaly = {
            'timestamp': pd.Timestamp.now().isoformat(),
            'type': anomaly_type,
            'message': message
        }
        
        self.anomaly_history.append(anomaly)
        
        if len(self.anomaly_history) > 1000:
            self.anomaly_history = self.anomaly_history[-1000:]
    
    def get_status(self) -> Dict[str, Any]:
        """获取监控状态"""
        latest_performance = self.performance_history[-1] if self.performance_history else None
        latest_anomalies = self.anomaly_history[-10:] if self.anomaly_history else []
        
        return {
            'is_running': self.is_running,
            'monitor_interval': self.monitor_interval,
            'positions_count': len(self.positions),
            'latest_performance': latest_performance,
            'recent_anomalies': latest_anomalies,
            'anomaly_count': len(self.anomaly_history)
        }
    
    def get_performance_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取绩效历史"""
        return self.performance_history[-limit:] if self.performance_history else []
    
    def get_anomaly_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取异常历史"""
        return self.anomaly_history[-limit:] if self.anomaly_history else []
    
    def set_monitor_interval(self, interval: int):
        """设置监控间隔"""
        self.monitor_interval = interval
        logger.info(f"监控间隔已设置为: {interval}秒")
