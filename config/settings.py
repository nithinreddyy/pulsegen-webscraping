"""
Configuration settings for Pulse - Module Extraction AI Agent
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    """Application settings loaded from environment variables"""
    
    # Azure OpenAI Configuration
    AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY', 'your_azure_openai_api_key_here')
    AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT', 'https://your-endpoint.openai.azure.com/')
    AZURE_OPENAI_DEPLOYMENT = os.getenv('AZURE_OPENAI_DEPLOYMENT', 'your-deployment-name')
    AZURE_OPENAI_API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview')
    
    # Firecrawl Configuration (Optional)
    FIRECRAWL_API_KEY = os.getenv('FIRECRAWL_API_KEY', 'your_firecrawl_api_key_here')
    
    # Application Configuration
    APP_TITLE = os.getenv('APP_TITLE', 'Pulse - Module Extraction AI Agent')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', '6000'))
    AI_TEMPERATURE = float(os.getenv('AI_TEMPERATURE', '0.1'))
    AI_MAX_TOKENS = int(os.getenv('AI_MAX_TOKENS', '2000'))
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    
    # Validation
    @classmethod
    def validate(cls):
        """Validate required settings"""
        required_settings = [
            ('AZURE_OPENAI_API_KEY', cls.AZURE_OPENAI_API_KEY),
            ('AZURE_OPENAI_ENDPOINT', cls.AZURE_OPENAI_ENDPOINT),
            ('AZURE_OPENAI_DEPLOYMENT', cls.AZURE_OPENAI_DEPLOYMENT),
        ]
        
        missing_settings = []
        for name, value in required_settings:
            if not value or value.startswith('your_'):
                missing_settings.append(name)
        
        if missing_settings:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_settings)}")
        
        return True

# Create settings instance
settings = Settings() 