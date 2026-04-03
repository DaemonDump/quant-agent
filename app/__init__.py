import os
from flask import Flask, request
from config import Config

def create_app(config_class=Config):
    app = Flask(__name__, 
                template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'),
                static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'))
    app.config.from_object(config_class)

    @app.after_request
    def _no_cache(resp):
        try:
            if request.path == '/' or resp.mimetype == 'text/html' or request.path.startswith('/api/'):
                resp.headers['Cache-Control'] = 'no-store, max-age=0'
                resp.headers['Pragma'] = 'no-cache'
                resp.headers['Expires'] = '0'
        except Exception:
            pass
        return resp

    # 配置 Jinja2 定界符以避免与 Vue.js 冲突
    app.jinja_env.variable_start_string = '{['
    app.jinja_env.variable_end_string = ']}'
    app.jinja_env.comment_start_string = '{#'
    app.jinja_env.comment_end_string = '#}'

    # Initialize Flask extensions here
    from . import db
    db.init_app(app)

    # Register blueprints here
    from .routes.main import main_bp
    app.register_blueprint(main_bp)

    from .routes.data import data_bp
    app.register_blueprint(data_bp)

    from .routes.backtest import backtest_bp
    app.register_blueprint(backtest_bp)

    from .routes.strategy import strategy_bp
    app.register_blueprint(strategy_bp)

    from .routes.ml import ml_bp
    app.register_blueprint(ml_bp)

    from .routes.monitor import monitor_bp
    app.register_blueprint(monitor_bp)

    from .routes.trading import trading_bp
    app.register_blueprint(trading_bp)

    return app
