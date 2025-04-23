import logging

# Configure logging
def setup_logger():

    # Set up logging format
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler()         # Log to console
        ]
    )
    logging.info("Logger initialized.")

# Call setup_logger to initialize logging when the package is imported
setup_logger()
