"""
机器学习量化模型系统 - 使用示例

展示如何使用 aiagent 模块进行模型训练和预测
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from aiagent.main import QuantMLSystem
from aiagent.config import Config


def example_training():
    """
    示例：训练模型
    """
    print("\n" + "="*60)
    print("示例：训练模型")
    print("="*60)
    
    # 创建系统
    config = Config()
    system = QuantMLSystem(config)
    
    # 定义股票池
    symbols = [
        '000001.SZ',  # 平安银行
        '600000.SH',  # 浦发银行
        '600036.SH',  # 招商银行
        '000002.SZ',  # 万科A
        '600519.SH',  # 贵州茅台
    ]
    
    # 定义时间范围
    start_date = '2020-01-01'
    end_date = '2024-12-31'
    
    try:
        # 执行训练流程
        results = system.train_pipeline(symbols, start_date, end_date)
        
        print("\n训练结果:")
        print(f"模型保存位置: {results['model_dir']}")
        print(f"特征数量: {len(results['feature_names'])}")
        print(f"验证集IC: {results['training_results']['val_metrics']['ic']:.4f}")
        print(f"验证集Rank IC: {results['training_results']['val_metrics']['rank_ic']:.4f}")
        
    except Exception as e:
        print(f"\n训练失败: {e}")
        print("请确保：")
        print("1. 已安装必要的依赖库（xgboost, lightgbm, pandas, numpy等）")
        print("2. 数据库中有足够的历史数据")
        print("3. Tushare API token已配置")


def example_prediction():
    """
    示例：使用模型进行预测
    """
    print("\n" + "="*60)
    print("示例：使用模型进行预测")
    print("="*60)
    
    # 创建系统
    config = Config()
    system = QuantMLSystem(config)
    
    # 构造预测请求
    request = {
        'request_id': 'test_request_001',
        'timestamp': '2026-03-27T09:30:00+08:00',
        'universe': ['000001.SZ', '600000.SH'],
        'feature_data': {
            '000001.SZ': {
                'close': 10.5,
                'volume': 1000000,
                'ma_20': 10.2,
                'rsi_14': 65.0,
                'macd': 0.5,
                'momentum_1m': 0.02,
                'volatility_20d': 0.015
            },
            '600000.SH': {
                'close': 8.5,
                'volume': 800000,
                'ma_20': 8.3,
                'rsi_14': 45.0,
                'macd': -0.2,
                'momentum_1m': -0.01,
                'volatility_20d': 0.012
            }
        }
    }
    
    try:
        # 执行预测
        response = system.predict(request)
        
        print("\n预测结果:")
        print(f"请求ID: {response['request_id']}")
        print(f"模型版本: {response['model_version']}")
        print(f"模型耗时: {response['model_latency_ms']:.2f}ms")
        print(f"状态: {response['status']}")
        
        if response['status'] == 'success':
            print("\n股票预测:")
            for symbol, pred in response['predictions'].items():
                print(f"\n{symbol}:")
                print(f"  预测分数: {pred['score']:.4f}")
                print(f"  预期收益: {pred['expected_return']:.2%}")
                print(f"  预测方向: {pred['direction']}")
                print(f"  置信度: {pred['confidence']:.2%}")
                print(f"  排名: {pred['rank']}")
        
        if response.get('warnings'):
            print("\n警告:")
            for warning in response['warnings']:
                print(f"  - {warning}")
        
    except Exception as e:
        print(f"\n预测失败: {e}")
        print("请确保：")
        print("1. 已有训练好的模型")
        print("2. 特征数据格式正确")


def example_model_info():
    """
    示例：获取模型信息
    """
    print("\n" + "="*60)
    print("示例：获取模型信息")
    print("="*60)
    
    # 创建系统
    config = Config()
    system = QuantMLSystem(config)
    
    try:
        # 获取模型信息
        model_info = system.get_model_info()
        
        print("\n模型信息:")
        print(f"模型名称: {model_info.get('model_name', 'N/A')}")
        print(f"模型版本: {model_info.get('version', 'N/A')}")
        print(f"模型类型: {model_info.get('model_type', 'N/A')}")
        print(f"特征数量: {model_info.get('feature_count', 'N/A')}")
        print(f"保存时间: {model_info.get('saved_at', 'N/A')}")
        print(f"生产就绪: {model_info.get('production_ready', 'N/A')}")
        
        if 'training_metrics' in model_info:
            print("\n训练指标:")
            metrics = model_info['training_metrics']
            print(f"  IC: {metrics.get('ic', 'N/A')}")
            print(f"  Rank IC: {metrics.get('rank_ic', 'N/A')}")
            print(f"  MSE: {metrics.get('mse', 'N/A')}")
            print(f"  R2: {metrics.get('r2', 'N/A')}")
        
    except Exception as e:
        print(f"\n获取模型信息失败: {e}")
        print("请确保已有训练好的模型")


def example_list_models():
    """
    示例：列出所有模型
    """
    print("\n" + "="*60)
    print("示例：列出所有模型")
    print("="*60)
    
    # 创建系统
    config = Config()
    system = QuantMLSystem(config)
    
    try:
        # 列出所有模型
        models = system.list_models()
        
        if not models:
            print("\n暂无模型")
        else:
            print("\n模型列表:")
            for model_name, versions in models.items():
                print(f"\n{model_name}:")
                for version, info in versions.items():
                    print(f"  {version}:")
                    print(f"    保存时间: {info.get('saved_at', 'N/A')}")
                    print(f"    生产就绪: {info.get('production_ready', 'N/A')}")
                    if 'metrics' in info:
                        print(f"    IC: {info['metrics'].get('ic', 'N/A')}")
        
    except Exception as e:
        print(f"\n列出模型失败: {e}")


def example_custom_config():
    """
    示例：使用自定义配置
    """
    print("\n" + "="*60)
    print("示例：使用自定义配置")
    print("="*60)
    
    # 创建自定义配置
    config = Config()
    
    # 修改模型类型
    config.model.model_type = 'lightgbm'
    
    # 修改训练参数
    config.training.n_estimators = 500
    config.training.max_depth = 8
    config.training.learning_rate = 0.05
    
    # 修改预测配置
    config.prediction.rate_limit_per_minute = 500
    config.prediction.enable_drift_detection = True
    
    print("\n自定义配置:")
    print(f"模型类型: {config.model.model_type}")
    print(f"训练轮数: {config.training.n_estimators}")
    print(f"最大深度: {config.training.max_depth}")
    print(f"学习率: {config.training.learning_rate}")
    print(f"速率限制: {config.prediction.rate_limit_per_minute} 次/分钟")
    print(f"分布漂移检测: {config.prediction.enable_drift_detection}")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("机器学习量化模型系统 - 使用示例")
    print("="*60)
    
    # 运行示例
    example_custom_config()
    example_model_info()
    example_list_models()
    
    # 训练和预测示例（需要数据）
    # example_training()
    # example_prediction()
    
    print("\n" + "="*60)
    print("示例运行完成")
    print("="*60)
    print("\n提示：")
    print("1. 首先运行 example_training() 训练模型")
    print("2. 然后运行 example_prediction() 进行预测")
    print("3. 使用 example_model_info() 查看模型信息")
    print("4. 使用 example_list_models() 列出所有模型")
    print("5. 使用 example_custom_config() 自定义配置")
