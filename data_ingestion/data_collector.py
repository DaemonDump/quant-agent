import tushare as ts
import pandas as pd
import sqlite3
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Optional
import os

logger = logging.getLogger(__name__)


class RealTimeDataCollector:
    def __init__(self, db_path: str = None):
        if db_path is None:
            root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(root, 'data', 'tushare', 'db', 'quant_data.db')
        self.db_path = db_path
        self.token = None
        self.pro = None
        self.symbols = []
        self.conn = sqlite3.connect(self.db_path)
        logger.info(f"数据库连接已打开: {self.db_path}")

    def close(self):
        if self.conn:
            self.conn.close()
            logger.info("数据库连接已关闭")

    def set_token(self, token: str):
        self.token = token
        try:
            self.pro = ts.pro_api(token)
            logger.info("Tushare API初始化成功")
        except Exception as e:
            logger.error(f"Tushare API初始化失败: {e}")
            self.pro = None
    
    def set_symbols(self, symbols: List[str]):
        self.symbols = symbols
        logger.info(f"设置监控标的: {symbols}")
    
    def collect_realtime_data(self) -> Dict[str, pd.DataFrame]:
        if not self.pro:
            logger.error("Tushare API未初始化")
            return {}
        
        if not self.symbols:
            logger.warning("未设置监控标的")
            return {}
        
        results = {}
        today = datetime.now().strftime('%Y%m%d')
        
        for symbol in self.symbols:
            try:
                df = self.pro.daily(ts_code=symbol, 
                                   start_date=today,
                                   end_date=today)
                
                if len(df) > 0:
                    cleaned_df = self.clean_data(df, symbol)
                    self.store_data(symbol, cleaned_df)
                    results[symbol] = cleaned_df
                    logger.info(f"成功采集{symbol}数据: {len(df)}条")
                else:
                    logger.warning(f"{symbol}无数据")
                    
            except Exception as e:
                logger.error(f"采集{symbol}数据失败: {e}")
        
        return results
    
    def collect_history_data(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        if not self.pro:
            logger.error("Tushare API未初始化")
            return None
        
        try:
            df_daily = ts.pro_bar(
                ts_code=symbol,
                api=self.pro,
                start_date=start_date,
                end_date=end_date,
                adj='qfq',
                freq='D',
                asset='E',
                adjfactor=False
            )
            df_moneyflow = self.pro.moneyflow(
                ts_code=symbol,
                start_date=start_date,
                end_date=end_date,
                fields='ts_code,trade_date,buy_lg_amount,net_mf_amount'
            )
            
            df_basic = self.pro.daily_basic(ts_code=symbol,
                                           start_date=start_date,
                                           end_date=end_date,
                                           fields='ts_code,trade_date,turnover_rate,pe_ttm,pb,total_mv,circ_mv')
            
            if len(df_daily) > 0:
                if len(df_basic) > 0:
                    df = pd.merge(
                        df_daily,
                        df_basic[['trade_date', 'turnover_rate', 'pe_ttm', 'pb', 'total_mv', 'circ_mv']],
                        on='trade_date',
                        how='left'
                    )
                else:
                    df = df_daily
                    df['turnover_rate'] = np.nan
                    df['pe_ttm'] = np.nan
                    df['pe'] = np.nan
                    df['pb'] = np.nan
                    df['total_mv'] = np.nan
                    df['circ_mv'] = np.nan
                if len(df_moneyflow) > 0:
                    df = pd.merge(
                        df,
                        df_moneyflow[['trade_date', 'buy_lg_amount', 'net_mf_amount']],
                        on='trade_date',
                        how='left'
                    )
                else:
                    df['buy_lg_amount'] = np.nan
                    df['net_mf_amount'] = np.nan
                if 'pe' not in df.columns:
                    df['pe'] = df.get('pe_ttm', np.nan)
                if 'change_pct' not in df.columns and 'pct_chg' in df.columns:
                    df['change_pct'] = df['pct_chg']
                if 'net_amount_rate' not in df.columns:
                    df['net_amount_rate'] = df['net_mf_amount'] / (df['amount'].replace(0, np.nan))
                df['adj_type'] = 'qfq'
                
                cleaned_df = self.clean_data(df, symbol)
                self.store_history_data(symbol, cleaned_df)
                logger.info(f"成功采集{symbol}前复权历史数据及指标: {len(df)}条")
                return cleaned_df
            else:
                logger.warning(f"{symbol}无历史数据")
                return None
                
        except Exception as e:
            logger.error(f"采集{symbol}历史数据失败: {e}")
            return None
    
    def clean_data(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        if df.empty:
            return df
        
        cleaned_df = df.copy()
        
        # 仅针对关键字段进行空值检查，忽略 PE/PB 因为很多股票可能确实没有
        # 如果强行 dropna 会把有行情没 PE/PB 的数据全删掉
        cleaned_df = cleaned_df.dropna(subset=['open', 'high', 'low', 'close', 'vol', 'amount'])
        
        cleaned_df = cleaned_df[
            (cleaned_df['high'] >= cleaned_df['low']) &
            (cleaned_df['close'] >= cleaned_df['low']) &
            (cleaned_df['close'] <= cleaned_df['high'])
        ]
        
        cleaned_df = cleaned_df[
            (cleaned_df['vol'] > 0) &
            (cleaned_df['amount'] > 0)
        ]
        
        cleaned_df = cleaned_df.sort_values('trade_date')
        cleaned_df = cleaned_df.reset_index(drop=True)
        
        logger.info(f"{symbol}数据清洗完成: {len(df)} -> {len(cleaned_df)}")
        return cleaned_df
    
    def _store_data(self, table_name: str, data: pd.DataFrame):
        try:
            data.to_sql(table_name, self.conn, if_exists='append', index=False)
            logger.info(f"成功存储{len(data)}条数据到 {table_name}")
        except Exception as e:
            logger.error(f"存储数据到 {table_name} 失败: {e}")

    def _upsert_data(self, table_name: str, columns: List[str], data: pd.DataFrame):
        if data.empty:
            return
        placeholders = ','.join(['?'] * len(columns))
        sql = f"INSERT OR REPLACE INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})"
        try:
            rows = [tuple(row[col] for col in columns) for _, row in data[columns].iterrows()]
            self.conn.executemany(sql, rows)
            self.conn.commit()
            logger.info(f"成功写入{len(rows)}条数据到 {table_name}")
        except Exception as e:
            self.conn.rollback()
            logger.error(f"写入数据到 {table_name} 失败: {e}")

    def store_data(self, symbol: str, data: pd.DataFrame):
        if data.empty:
            return

        df_to_store = data.copy()
        df_to_store['symbol'] = symbol
        df_to_store.rename(columns={
            'trade_date': 'timestamp',
            'close': 'price',
            'vol': 'volume',
            'open': 'open_price',
            'high': 'high_price',
            'low': 'low_price'
        }, inplace=True)
        
        cols = ['symbol', 'timestamp', 'price', 'volume', 'amount', 'open_price', 'high_price', 'low_price']
        self._upsert_data('stock_realtime_data', cols, df_to_store[cols])

    def store_history_data(self, symbol: str, data: pd.DataFrame):
        if data.empty:
            return

        df_to_store = data.copy()
        df_to_store['symbol'] = symbol
        rename_map = {
            'close': 'close_price',
            'vol': 'volume',
            'open': 'open_price',
            'high': 'high_price',
            'low': 'low_price'
        }
        for src, dst in rename_map.items():
            if src in df_to_store.columns and dst not in df_to_store.columns:
                df_to_store.rename(columns={src: dst}, inplace=True)
        if 'pct_chg' in df_to_store.columns:
            if 'change_pct' in df_to_store.columns:
                df_to_store['change_pct'] = df_to_store['change_pct'].fillna(df_to_store['pct_chg'])
                df_to_store.drop(columns=['pct_chg'], inplace=True)
            else:
                df_to_store.rename(columns={'pct_chg': 'change_pct'}, inplace=True)
        if 'pe_ttm' in df_to_store.columns:
            if 'pe' in df_to_store.columns:
                df_to_store['pe'] = df_to_store['pe'].fillna(df_to_store['pe_ttm'])
                df_to_store.drop(columns=['pe_ttm'], inplace=True)
            else:
                df_to_store.rename(columns={'pe_ttm': 'pe'}, inplace=True)
        if 'adj_type' not in df_to_store.columns:
            df_to_store['adj_type'] = 'qfq'
        cols = [
            'symbol', 'trade_date', 'open_price', 'high_price', 'low_price', 'close_price',
            'pre_close', 'change_pct', 'volume', 'amount', 'pe', 'pb', 'turnover_rate',
            'total_mv', 'circ_mv', 'buy_lg_amount', 'net_mf_amount', 'net_amount_rate', 'adj_type'
        ]
        for col in cols:
            if col not in df_to_store.columns:
                df_to_store[col] = np.nan
        self._upsert_data('stock_history_data', cols, df_to_store[cols])
    
    def validate_data(self, symbol: str) -> Dict[str, any]:
        try:
            query = '''
                SELECT COUNT(*) as count,
                       MIN(timestamp) as min_time,
                       MAX(timestamp) as max_time
                FROM stock_realtime_data
                WHERE symbol = ?
            '''
            df = pd.read_sql_query(query, self.conn, params=(symbol,))
            
            if len(df) > 0 and df.iloc[0]['count'] > 0:
                result = {
                    'symbol': symbol,
                    'data_count': int(df.iloc[0]['count']),
                    'min_time': df.iloc[0]['min_time'],
                    'max_time': df.iloc[0]['max_time'],
                    'is_valid': True
                }
                
                max_time = pd.to_datetime(result['max_time'])
                time_diff = (datetime.now() - max_time).total_seconds()
                
                if time_diff > 3600:
                    result['is_valid'] = False
                    result['message'] = f'数据延迟{int(time_diff/60)}分钟'
                else:
                    result['message'] = '数据正常'
                
                return result
            else:
                return {
                    'symbol': symbol,
                    'data_count': 0,
                    'is_valid': False,
                    'message': '无数据'
                }
                
        except Exception as e:
            logger.error(f"验证{symbol}数据失败: {e}")
            return {
                'symbol': symbol,
                'is_valid': False,
                'message': f'验证失败: {str(e)}'
            }
    
    def get_realtime_data(self, symbol: str, limit: int = 10) -> pd.DataFrame:
        try:
            query = '''
                SELECT * FROM stock_realtime_data
                WHERE symbol = ?
                ORDER BY timestamp DESC
                LIMIT ?
            '''
            df = pd.read_sql_query(query, self.conn, params=(symbol, limit))
            return df
        except Exception as e:
            logger.error(f"获取{symbol}实时数据失败: {e}")
            return pd.DataFrame()
    
    def get_history_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        try:
            query = '''
                SELECT * FROM stock_history_data
                WHERE symbol = ? AND trade_date >= ? AND trade_date <= ?
                ORDER BY trade_date ASC
            '''
            df = pd.read_sql_query(query, self.conn, params=(symbol, start_date, end_date))
            return df
        except Exception as e:
            logger.error(f"获取{symbol}历史数据失败: {e}")
            return pd.DataFrame()
    
    def get_all_symbols(self) -> List[str]:
        try:
            query = '''
                SELECT DISTINCT symbol FROM stock_realtime_data
            '''
            df = pd.read_sql_query(query, self.conn)
            return df['symbol'].tolist()
        except Exception as e:
            logger.error(f"获取标的列表失败: {e}")
            return []
