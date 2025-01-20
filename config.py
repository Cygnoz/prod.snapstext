import os

class Config:
    UPLOAD_FOLDER = 'uploads'
    # Other configuration variables

    @staticmethod
    def init_app(app):
        # Create upload directory if it doesn't exist
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])