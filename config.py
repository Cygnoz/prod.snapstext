import os
from dotenv import load_dotenv


class Config:
    load_dotenv()
    # Secret key for JWT token
    SECRET_KEY = os.getenv('JWT_SECRET')
    
    # Upload folder configuration
    UPLOAD_FOLDER = 'uploads'
    
    # Ensure upload folder exists
    @classmethod
    def init_app(cls, app):
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])