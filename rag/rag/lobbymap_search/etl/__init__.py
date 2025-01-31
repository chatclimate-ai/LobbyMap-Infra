import logging
import os

# Configure logging
def setup_logger(log_dir="logs"):
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'lobbymap-pipeline.log')

    # Set up logging format
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),  # Log to file
            logging.StreamHandler()         # Log to console
        ]
    )
    logging.info("Logger initialized.")

# Call setup_logger to initialize logging when the package is imported
setup_logger()
