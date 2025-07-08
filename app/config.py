import logging

def setup_logging():
    logging.basicConfig(level=logging.INFO)

def get_cors_settings():
    return {
        "allow_origins": ["http://localhost:3000"],
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
