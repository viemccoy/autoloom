import os
from dotenv import load_dotenv

def read_config():
    """Read configuration from environment variables"""
    load_dotenv()
    
    config = {
        'HYPERBOLIC_API_KEY': os.getenv('HYPERBOLIC_API_KEY'),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY')
    }
    
    if not config['HYPERBOLIC_API_KEY']:
        raise ValueError('HYPERBOLIC_API_KEY is not set in .env file')
    
    if not config['OPENAI_API_KEY']:
        raise ValueError('OPENAI_API_KEY is not set in .env file')
        
    return config