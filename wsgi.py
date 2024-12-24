from app import app
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    try:
        port = int(os.getenv("PORT", 5000))
        logger.info(f"Starting production server on port {port}")
        app.run(
            host="0.0.0.0",
            port=port,
            debug=False,
            threaded=True
        )
    except Exception as e:
        logger.error(f"Server startup failed: {str(e)}")
        raise