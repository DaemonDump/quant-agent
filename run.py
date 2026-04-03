import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

app = create_app()

if __name__ == '__main__':
    host = os.environ.get('HOST') or '127.0.0.1'
    port = int(os.environ.get('PORT') or 5000)
    debug = (os.environ.get('FLASK_DEBUG') or '0') not in ('0', 'false', 'False')
    app.run(host=host, port=port, debug=debug, use_reloader=False)
