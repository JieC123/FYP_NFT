from flask import Flask
from app.config import Config
from app.extensions import mail

def create_app(config_class=Config):
    app = Flask(__name__, 
                template_folder='../src',
                static_folder='../src',
                static_url_path='/static')
    
    app.config.from_object(config_class)
    
    # Initialize extensions
    mail.init_app(app)
    
    # Import blueprints here (after extensions are initialized)
    from app.routes.user_routes import user_bp
    from app.routes.organizer_routes import organizer_bp
    
    # Register blueprints
    app.register_blueprint(user_bp)
    app.register_blueprint(organizer_bp, url_prefix='/org')
    
    return app