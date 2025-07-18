# Pulse - Module Extraction AI Agent

![Pulse Logo](Pulse.jpg)

A powerful AI-driven web scraping and content extraction tool that automatically extracts structured modules and submodules from any documentation website. Built with Streamlit and powered by Azure OpenAI.

## Features

### Core Capabilities
- **Universal Web Scraping**: Extracts content from any documentation website
- **AI-Powered Analysis**: Uses Azure OpenAI GPT-4 to intelligently structure content
- **Anti-Bot Evasion**: Multiple extraction strategies to bypass protection mechanisms
- **Guaranteed Results**: Always returns meaningful content with intelligent fallbacks
- **Real-time Processing**: Live progress tracking with time estimates
- **Quality Validation**: Ensures extracted modules meet quality standards

### Advanced Features
- **Multi-Layer Extraction**: 6-layer approach (Basic → Stealth → Selenium → Firecrawl → Alternatives)
- **Dynamic Content Support**: Handles JavaScript-rendered pages with Selenium
- **Firecrawl Integration**: Advanced scraping for heavily protected sites
- **Comprehensive Logging**: Detailed logs and debug information
- **Session Management**: Prevents data loss during processing
- **Export Capabilities**: Download results as structured JSON

## Project Structure

```
Pulsegen/
├── app.py                 # Main Streamlit application
├── config/                # Configuration management
│   ├── __init__.py
│   └── settings.py        # Environment variables and settings
├── extractor/             # Core extraction modules
│   ├── __init__.py
│   ├── crawler.py         # Web crawling and content extraction
│   └── inference.py       # AI-powered module extraction
├── debug/                 # Debug files (auto-generated)
├── logs/                  # Application logs (auto-generated)
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
├── LICENSE               # MIT License
└── README.md             # This file
```

## Prerequisites

- **Python 3.8+**: Make sure you have Python 3.8 or higher installed
- **Azure OpenAI Access**: You need an Azure OpenAI API key and endpoint
- **Chrome Browser**: Required for Selenium (dynamic content extraction)
- **Firecrawl API**: For advanced scraping of protected sites

## Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/nithnreddyy/pulsegen-webscraping.git
cd pulsegen
```

### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

#### Step 1: Copy the template
```bash
# Windows
copy .env .env

# macOS/Linux
cp .env .env
```

#### Step 2: Get your Azure OpenAI credentials

1. **Go to Azure Portal**: Visit [portal.azure.com](https://portal.azure.com/)
2. **Navigate to your Azure OpenAI resource**
3. **Get API Key & Endpoint**:
   - Go to "Keys and Endpoint" section
   - Copy **Key 1** or **Key 2**
   - Copy the **Endpoint** URL
4. **Get Deployment Name**:
   - Go to "Model deployments" section
   - Note your GPT-4 deployment name

#### Step 3: Edit the .env file

Open `.env` in your text editor and replace the placeholders:

```env
# =============================================================================
# Pulse - Module Extraction AI Agent - Environment Configuration
# Copy this file to .env and replace placeholders with your actual credentials

# AZURE OPENAI CONFIGURATION (REQUIRED)
AZURE_OPENAI_API_KEY=your_actual_32_character_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-actual-resource-name.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your-actual-gpt-4-deployment-name
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# FIRECRAWL CONFIGURATION (OPTIONAL)
FIRECRAWL_API_KEY=fc-your_actual_firecrawl_api_key_here
```

#### Example of properly configured .env:
```env
# AZURE OPENAI CONFIGURATION (REQUIRED)
AZURE_OPENAI_API_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
AZURE_OPENAI_ENDPOINT=https://mycompany-openai.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4-turbo
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# FIRECRAWL CONFIGURATION (REQUIRED)
FIRECRAWL_API_KEY=fc-1234567890abcdef1234567890abcdef
```

### 5. Run the Application
```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

## Usage Guide

### Basic Usage
1. **Enter URLs**: Add documentation URLs (one per line) in the text area
2. **Click Extract**: Press "Extract Modules" to start processing
3. **Monitor Progress**: Watch real-time progress with time estimates
4. **Review Results**: Examine extracted modules with quality indicators
5. **Download**: Export results as JSON files

### Understanding Results
- **High Quality**: Successfully extracted with AI analysis
- **Medium Quality**: Extracted using fallback content
- **Skipped**: URLs that couldn't produce meaningful modules

## Output Format

The system generates structured JSON in this format:

```json
[
  {
    "module": "User Authentication",
    "Description": "Comprehensive user authentication system including login, registration, password management, and security features. Supports multiple authentication methods and provides secure session management.",
    "Submodules": {
      "Login System": "Complete login functionality with email/username support, password validation, and remember me options.",
      "Password Reset": "Secure password reset workflow with email verification and temporary token generation.",
      "Two-Factor Authentication": "Enhanced security with 2FA support including SMS and authenticator app integration."
    }
  }
]
```

## Configuration Options

### Required Environment Variables

| Variable | Description | Example | Where to Get |
|----------|-------------|---------|--------------|
| `AZURE_OPENAI_API_KEY` | Your Azure OpenAI API key | `a1b2c3d4e5f6...` | Azure Portal → OpenAI → Keys and Endpoint |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | `https://mycompany-openai.openai.azure.com/` | Azure Portal → OpenAI → Keys and Endpoint |
| `AZURE_OPENAI_DEPLOYMENT` | Your GPT-4 deployment name | `gpt-4-turbo` | Azure Portal → OpenAI → Model deployments |
| `AZURE_OPENAI_API_VERSION` | API version | `2024-02-15-preview` | Usually keep default |

### Optional Environment Variables

| Variable | Description | Default | Where to Get |
|----------|-------------|---------|--------------|
| `FIRECRAWL_API_KEY` | Firecrawl API key for advanced scraping | - | [firecrawl.dev](https://firecrawl.dev/) |

### Additional Configuration
You can also set these in your `.env` file for customization:
```env
# Application Settings (Optional)
APP_TITLE=Pulse - Module Extraction AI Agent
MAX_CONTENT_LENGTH=6000
AI_TEMPERATURE=0.1
AI_MAX_TOKENS=2000
LOG_LEVEL=INFO
DEBUG_MODE=false
```

## How It Works

### Multi-Layer Content Extraction
The system uses a progressive approach to extract content:

1. **Basic Request**: Standard HTTP request with stealth headers
2. **Stealth Session**: Advanced headers and session warming
3. **Advanced Stealth**: Multiple user agents and proxy headers
4. **Selenium**: JavaScript rendering for dynamic content
5. **Firecrawl**: Professional scraping service for protected sites
6. **Alternative URLs**: Try different URL patterns

### AI-Powered Module Extraction
- **Content Analysis**: AI analyzes extracted content for structure
- **Module Identification**: Identifies main topics and sections
- **Submodule Extraction**: Finds detailed features and components
- **Quality Validation**: Ensures meaningful and detailed results
- **Fallback Generation**: Creates structured content when AI fails

## Known Limitations

- **Extraction from Non-Standard Docs**: Sites with highly custom navigation, heavy client-side routing, or unusual markup may yield incomplete or fragmented results.
- **Rate Limiting & Captchas**: Some sites may temporarily block requests or present CAPTCHAs, which cannot be bypassed automatically.
- **Session/Stateful Content**: Pages requiring login, cookies, or session state are not supported and will not be extracted.
- **API/Quota Exhaustion**: If your Azure OpenAI or Firecrawl quota is exhausted, extraction will silently fail or degrade in quality.
- **Very Large Pages**: Extremely large documentation pages may be truncated due to content length limits, potentially omitting some modules.
- **Non-English/Multilingual Docs**: Extraction is optimized for English. Results on other languages may be inconsistent.
- **Frequent Source Changes**: If the target documentation site changes structure often, extraction logic may break until updated.
- **No Interactive Content**: Interactive demos, embedded videos, or widgets are not extracted—only static text and structure.

## Video Explanation

https://drive.google.com/file/d/1OSQFPA0h_A54gMdM2uFnAbBlEILU_GWl/view?usp=sharing

## Sample UI Screenshots

Sample screenshots of the Streamlit UI are included in this folder:

![Streamlit UI Screenshot 1](UI-1.PNG)
*Main dashboard view*

![Streamlit UI Screenshot 2](UI-2.PNG)
*Extraction results view*

These images showcase the application's interface and user experience.
