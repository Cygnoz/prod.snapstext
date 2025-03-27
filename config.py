class Config:
    # Other configuration variables

    @staticmethod
    def init_app(app):
        """Configure the app with necessary settings."""
        app.config['SOME_SETTING'] = 'value'
        print("App initialized with custom settings.")
