import os
import shutil
import secrets
import warnings

class Config:
    _env_key = os.environ.get('SECRET_KEY')
    if not _env_key:
        warnings.warn(
            "SECRET_KEY 未通过环境变量设置，已自动生成随机密钥。"
            "生产环境请在 .env 中设置 SECRET_KEY。",
            stacklevel=2
        )
    SECRET_KEY = _env_key or secrets.token_hex(32)
    _ROOT = os.path.dirname(os.path.abspath(__file__))
    _DATA_DIR = os.path.join(_ROOT, 'data', 'tushare')
    _DB_DIR = os.path.join(_DATA_DIR, 'db')
    _NEW_DB = os.path.join(_DB_DIR, 'quant_data.db')
    _OLD_DB = os.path.join(_ROOT, 'quant_data.db')

    os.makedirs(_DB_DIR, exist_ok=True)
    if (not os.path.exists(_NEW_DB)) and os.path.exists(_OLD_DB):
        shutil.copy2(_OLD_DB, _NEW_DB)

    DATABASE = _NEW_DB
    LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs/app.log')
    LOG_LEVEL = 'INFO'
