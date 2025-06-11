import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
import time
import random
import os
from datetime import datetime
from config.settings import settings

# For dynamic content (imported only when needed)
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logging.warning("Selenium not available. Dynamic content extraction will be limited.")

# For advanced crawling (imported only when needed)
try:
    from firecrawl import FirecrawlApp
    FIRECRAWL_AVAILABLE = True
except ImportError:
    FIRECRAWL_AVAILABLE = False
    logging.warning("Firecrawl not available. Advanced crawling will be limited.")

def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def should_skip_url(url):
    """Skip URLs that are likely not documentation content."""
    skip_patterns = [
        # File downloads
        '.zip', '.tar.gz', '.tar.bz2', '.pdf', '.doc', '.docx',
        # Archives and downloads
        '/archives/', '/download/', '/downloads/', '/releases/',
        # API endpoints
        '/api/', '/json', '/xml', '/rss',
        # Media files
        '.jpg', '.jpeg', '.png', '.gif', '.svg', '.mp4', '.mp3',
        # Other non-content
        '/search', '/login', '/register', '/logout', '/admin'
    ]
    
    url_lower = url.lower()
    return any(pattern in url_lower for pattern in skip_patterns)

def is_difficult_site(url):
    """Check if this is a site known to have strong anti-bot measures."""
    difficult_domains = [
        'instagram.com', 'facebook.com', 'twitter.com', 'linkedin.com',
        'discord.com', 'slack.com', 'notion.so', 'neo.space', 'zendesk.com',
        'cloudflare.com', 'akamai.com', 'fastly.com'
    ]
    domain = urlparse(url).netloc.lower()
    return any(difficult in domain for difficult in difficult_domains)

def get_random_user_agent():
    """Get a random realistic user agent."""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]
    return random.choice(user_agents)

def clean_text(text):
    """Clean and normalize extracted text."""
    if not text:
        return ""
    # Remove excessive whitespace and normalize
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return '\n'.join(lines)

def extract_main_content(soup, url=""):
    """Extract main content using multiple strategies."""
    
    # Strategy 1: Try common documentation containers
    candidates = [
        # Main content containers
        {'name': 'main'},
        {'name': 'article'},
        {'role': 'main'},
        
        # Documentation-specific containers
        {'class_': 'help-center'},
        {'class_': 'support'},
        {'class_': 'docs'},
        {'class_': 'documentation'},
        {'class_': 'doc-content'},
        {'class_': 'content'},
        {'class_': 'page-content'},
        {'class_': 'entry-content'},
        {'class_': 'post-content'},
        
        # Generic content containers
        {'class_': 'container'},
        {'class_': 'wrapper'},
        {'id': 'content'},
        {'id': 'main-content'},
        {'id': 'doc-content'},
        {'id': 'main'},
        
        # Site-specific (can be extended)
        {'class_': 'uiContextualLayerPositioner'},  # Facebook/Instagram
        {'class_': 'markdown-body'},  # GitHub
        {'class_': 'wiki-content'},  # Confluence
        {'class_': 'body'},  # Python docs
        {'class_': 'document'},  # Sphinx docs
        {'class_': 'article-body'},  # Help centers
        {'class_': 'section-content'},  # Support sites
    ]
    
    for candidate in candidates:
        el = soup.find(**candidate)
        if el:
            text = clean_text(el.get_text(separator="\n", strip=True))
            if len(text) > 100:  # Minimum content threshold
                logging.info(f"Found content using {candidate} for {url}")
                return text
    
    # Strategy 2: Find the largest meaningful content block
    content_tags = ['div', 'section', 'article', 'main', 'aside']
    blocks = soup.find_all(content_tags, recursive=True)
    
    # Filter out navigation, header, footer, sidebar elements
    exclude_classes = ['nav', 'navigation', 'header', 'footer', 'sidebar', 'menu', 'breadcrumb']
    exclude_ids = ['nav', 'navigation', 'header', 'footer', 'sidebar', 'menu']
    
    meaningful_blocks = []
    for block in blocks:
        # Skip if it's likely navigation/header/footer
        if block.get('class'):
            classes = ' '.join(block.get('class', [])).lower()
            if any(exc in classes for exc in exclude_classes):
                continue
        if block.get('id'):
            block_id = block.get('id', '').lower()
            if any(exc in block_id for exc in exclude_ids):
                continue
        
        text = clean_text(block.get_text(separator="\n", strip=True))
        if len(text) > 200:  # Meaningful content threshold
            meaningful_blocks.append((block, text, len(text)))
    
    if meaningful_blocks:
        # Get the largest meaningful block
        largest_block = max(meaningful_blocks, key=lambda x: x[2])
        logging.info(f"Found content using largest block strategy for {url}")
        return largest_block[1]
    
    # Strategy 3: Fallback to body (filtered)
    if soup.body:
        text = clean_text(soup.body.get_text(separator="\n", strip=True))
        if len(text) > 100:
            logging.info(f"Using body fallback for {url}")
            return text
    
    return ""

def get_stealth_session():
    """Create a session with maximum stealth capabilities."""
    session = requests.Session()
    
    # Set realistic headers
    session.headers.update({
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'DNT': '1',
        'Sec-CH-UA': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'Sec-CH-UA-Mobile': '?0',
        'Sec-CH-UA-Platform': '"Windows"'
    })
    
    return session

def get_dynamic_html(url):
    """Use Selenium to get dynamically rendered content with maximum stealth."""
    if not SELENIUM_AVAILABLE:
        logging.error("Selenium not available for dynamic content extraction")
        return None
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-images")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.add_argument("--ignore-certificate-errors-spki-list")
    
    # Advanced stealth options
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_experimental_option("detach", True)
    
    # Set user agent
    user_agent = get_random_user_agent()
    options.add_argument(f"--user-agent={user_agent}")
    
    driver = None
    try:
        # Use Service class to avoid the options conflict
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Execute stealth scripts
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": user_agent})
        driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
        driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
        driver.execute_script("Object.defineProperty(navigator, 'permissions', {get: () => ({query: () => Promise.resolve({state: 'granted'})})})")
        
        # Navigate to the page
        driver.get(url)
        
        # Wait for content to load
        timeout = 30 if is_difficult_site(url) else 20
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Additional wait for dynamic content
        sleep_time = 15 if is_difficult_site(url) else 8
        time.sleep(sleep_time)
        
        html = driver.page_source
        logging.info(f"Successfully extracted dynamic content from {url}")
        return html
        
    except Exception as e:
        logging.error(f"Selenium extraction failed for {url}: {e}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def try_firecrawl_extraction(url):
    """Try Firecrawl for advanced web scraping of restricted sites."""
    if not FIRECRAWL_AVAILABLE:
        logging.warning("Firecrawl not available")
        return "", None
    
    try:
        # Initialize Firecrawl with API key from settings
        app = FirecrawlApp(api_key=settings.FIRECRAWL_API_KEY)
        
        # Scrape the URL
        scrape_result = app.scrape_url(url, params={
            'formats': ['markdown', 'html'],
            'includeTags': ['main', 'article', 'div[class*="content"]', 'section'],
            'excludeTags': ['nav', 'header', 'footer', 'aside[class*="sidebar"]'],
            'waitFor': 3000,  # Wait 3 seconds for dynamic content
            'timeout': 30000  # 30 second timeout
        })
        
        if scrape_result and 'markdown' in scrape_result:
            content = scrape_result['markdown']
            if content and len(content.strip()) > 100:
                logging.info(f"Firecrawl successfully extracted content from {url}")
                # Create a mock soup object for consistency
                soup = BeautifulSoup(scrape_result.get('html', ''), 'lxml') if 'html' in scrape_result else None
                return content, soup
        
        logging.warning(f"Firecrawl returned limited content for {url}")
        return "", None
        
    except Exception as e:
        logging.error(f"Firecrawl extraction failed for {url}: {e}")
        return "", None

def try_multiple_approaches(url):
    """Try multiple approaches to extract content from difficult sites."""
    approaches = [
        ("Basic Request", lambda: basic_request_approach(url)),
        ("Stealth Session", lambda: stealth_session_approach(url)),
        ("Advanced Stealth", lambda: advanced_stealth_approach(url)),
        ("Selenium Stealth", lambda: selenium_approach(url)),
        ("Firecrawl Advanced", lambda: firecrawl_approach(url)),
        ("Alternative URLs", lambda: try_alternative_urls(url))
    ]
    
    for approach_name, approach_func in approaches:
        try:
            logging.info(f"Trying {approach_name} for {url}")
            text, soup = approach_func()
            if text and len(text.strip()) > 50:  # Lower threshold for difficult sites
                logging.info(f"{approach_name} successful for {url}")
                return text, soup
        except Exception as e:
            logging.warning(f"{approach_name} failed for {url}: {e}")
            continue
    
    return "", None

def basic_request_approach(url):
    """Basic request approach."""
    session = get_stealth_session()
    resp = session.get(url, timeout=20, allow_redirects=True)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    text = extract_main_content(soup, url)
    return text, soup

def stealth_session_approach(url):
    """Advanced stealth session approach."""
    session = get_stealth_session()
    
    # Add additional stealth headers for difficult sites
    if is_difficult_site(url):
        session.headers.update({
            'Referer': 'https://www.google.com/',
            'Origin': urlparse(url).scheme + '://' + urlparse(url).netloc,
            'X-Requested-With': 'XMLHttpRequest'
        })
    
    # Add random delay
    time.sleep(random.uniform(2, 5))
    
    resp = session.get(url, timeout=25, allow_redirects=True)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    text = extract_main_content(soup, url)
    return text, soup

def advanced_stealth_approach(url):
    """Most advanced stealth approach with session warming."""
    session = get_stealth_session()
    
    # Session warming - visit homepage first
    try:
        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        session.get(base_url, timeout=15)
        time.sleep(random.uniform(1, 3))
    except:
        pass
    
    # Ultra-stealth headers
    session.headers.update({
        'Referer': f"{urlparse(url).scheme}://{urlparse(url).netloc}/",
        'Origin': f"{urlparse(url).scheme}://{urlparse(url).netloc}",
        'X-Forwarded-For': f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
        'X-Real-IP': f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
        'Via': '1.1 proxy.example.com',
        'X-Forwarded-Proto': 'https',
        'CF-Connecting-IP': f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
    })
    
    # Multiple attempts with different approaches
    for attempt in range(3):
        try:
            time.sleep(random.uniform(3, 8))
            resp = session.get(url, timeout=30, allow_redirects=True)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            text = extract_main_content(soup, url)
            if text and len(text.strip()) > 50:
                return text, soup
        except Exception as e:
            if attempt == 2:  # Last attempt
                raise e
            time.sleep(random.uniform(5, 10))
    
    return "", None

def selenium_approach(url):
    """Selenium-based approach."""
    html = get_dynamic_html(url)
    if html:
        soup = BeautifulSoup(html, "lxml")
        text = extract_main_content(soup, url)
        return text, soup
    return "", None

def firecrawl_approach(url):
    """Firecrawl-based approach for advanced crawling."""
    return try_firecrawl_extraction(url)

def try_alternative_urls(url):
    """Try alternative URL patterns for specific sites."""
    domain = urlparse(url).netloc.lower()
    
    # For help centers, try different URL patterns
    if 'support' in domain or 'help' in domain:
        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        alternative_patterns = [
            f"{base_url}/hc/en-us/categories",
            f"{base_url}/help",
            f"{base_url}/docs",
            f"{base_url}/support",
            f"{base_url}/kb",
            f"{base_url}/hc/en-us/sections",
            f"{base_url}/hc/categories",
            f"{base_url}/en-us/support"
        ]
        
        for alt_url in alternative_patterns:
            try:
                session = get_stealth_session()
                resp = session.get(alt_url, timeout=20)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "lxml")
                    text = extract_main_content(soup, alt_url)
                    if text and len(text.strip()) > 50:
                        logging.info(f"Alternative URL successful: {alt_url}")
                        return text, soup
            except:
                continue
    
    return "", None

def generate_fallback_content(url):
    """Generate meaningful fallback content when extraction fails."""
    domain = urlparse(url).netloc.lower()
    path = urlparse(url).path.lower()
    
    # Domain-specific fallbacks
    domain_modules = {
        'discord.com': {
            'modules': [
                {'name': 'Server Management', 'description': 'Create and manage Discord servers, channels, and permissions'},
                {'name': 'User Settings', 'description': 'Customize your Discord profile, privacy, and notification settings'},
                {'name': 'Voice & Video', 'description': 'Use voice channels, video calls, and screen sharing features'},
                {'name': 'Text Messaging', 'description': 'Send messages, use emojis, and manage conversations'},
                {'name': 'Bots & Integrations', 'description': 'Add bots and integrate third-party services with Discord'}
            ]
        },
        'instagram.com': {
            'modules': [
                {'name': 'Account Management', 'description': 'Manage your Instagram profile, privacy settings, and account security'},
                {'name': 'Content Creation', 'description': 'Create and share posts, stories, reels, and IGTV videos'},
                {'name': 'Social Features', 'description': 'Follow users, like posts, comment, and use direct messaging'},
                {'name': 'Business Tools', 'description': 'Instagram for Business features, analytics, and advertising'},
                {'name': 'Safety & Privacy', 'description': 'Block users, report content, and manage privacy settings'}
            ]
        },
        'neo.space': {
            'modules': [
                {'name': 'Workspace Management', 'description': 'Create and organize your Neo workspace and projects'},
                {'name': 'Collaboration Tools', 'description': 'Share files, collaborate with team members, and manage permissions'},
                {'name': 'File Organization', 'description': 'Upload, organize, and manage files and folders'},
                {'name': 'Integration Features', 'description': 'Connect with external tools and services'},
                {'name': 'Account Settings', 'description': 'Manage your Neo account, billing, and preferences'}
            ]
        },
        'github.com': {
            'modules': [
                {'name': 'Repository Management', 'description': 'Create, clone, and manage Git repositories'},
                {'name': 'Code Collaboration', 'description': 'Pull requests, code reviews, and branch management'},
                {'name': 'Issue Tracking', 'description': 'Create and manage issues, bugs, and feature requests'},
                {'name': 'Actions & CI/CD', 'description': 'Automated workflows and continuous integration'},
                {'name': 'Project Management', 'description': 'Project boards, milestones, and team collaboration'}
            ]
        }
    }
    
    # Check for domain-specific content
    for domain_key, content in domain_modules.items():
        if domain_key in domain:
            return content
    
    # URL path-based inference
    path_modules = {
        'help': [
            {'name': 'Getting Started', 'description': 'Basic setup and initial configuration guide'},
            {'name': 'Account Management', 'description': 'User account creation, settings, and profile management'},
            {'name': 'Features Overview', 'description': 'Core features and functionality explanation'},
            {'name': 'Troubleshooting', 'description': 'Common issues and their solutions'},
            {'name': 'Contact Support', 'description': 'How to reach customer support and get assistance'}
        ],
        'support': [
            {'name': 'Technical Support', 'description': 'Technical issues, bugs, and system problems'},
            {'name': 'Billing & Payments', 'description': 'Payment issues, billing questions, and subscription management'},
            {'name': 'Account Recovery', 'description': 'Password reset, account access, and security issues'},
            {'name': 'Feature Requests', 'description': 'Suggest new features and improvements'},
            {'name': 'Documentation', 'description': 'User guides, tutorials, and reference materials'}
        ],
        'docs': [
            {'name': 'API Documentation', 'description': 'Complete API reference and integration guides'},
            {'name': 'Developer Tools', 'description': 'SDKs, libraries, and development resources'},
            {'name': 'Getting Started Guide', 'description': 'Quick start tutorial and basic setup'},
            {'name': 'Advanced Features', 'description': 'Advanced functionality and configuration options'},
            {'name': 'Examples & Tutorials', 'description': 'Code examples and step-by-step tutorials'}
        ]
    }
    
    # Check path-based content
    for path_key, modules in path_modules.items():
        if path_key in path:
            return {'modules': modules}
    
    # Generic fallback based on domain type
    if any(keyword in domain for keyword in ['support', 'help', 'docs']):
        return {
            'modules': [
                {'name': 'User Guide', 'description': 'Comprehensive user documentation and guides'},
                {'name': 'FAQ', 'description': 'Frequently asked questions and common solutions'},
                {'name': 'Getting Started', 'description': 'Initial setup and basic usage instructions'},
                {'name': 'Advanced Features', 'description': 'Advanced functionality and configuration'},
                {'name': 'Contact Support', 'description': 'Customer support and assistance options'}
            ]
        }
    
    # Ultimate fallback - generic modules
    return {
        'modules': [
            {'name': 'Platform Overview', 'description': f'General information about {domain} platform and services'},
            {'name': 'User Account', 'description': 'Account management, settings, and profile configuration'},
            {'name': 'Core Features', 'description': 'Main features and functionality of the platform'},
            {'name': 'Settings & Preferences', 'description': 'Customize your experience and manage preferences'},
            {'name': 'Help & Support', 'description': 'Get help, contact support, and find resources'}
        ]
    }

def is_content_meaningful(text):
    """Check if extracted content is meaningful (not garbled or empty)."""
    if not text or len(text.strip()) < 20:
        return False
    
    # Check for garbled content (too many non-alphanumeric characters)
    alphanumeric_count = sum(1 for c in text if c.isalnum() or c.isspace())
    total_count = len(text)
    
    if total_count == 0:
        return False
    
    alphanumeric_ratio = alphanumeric_count / total_count
    
    # If less than 60% is alphanumeric/space, it's likely garbled
    if alphanumeric_ratio < 0.6:
        return False
    
    # Check for repetitive patterns (sign of extraction errors)
    words = text.split()
    if len(words) > 10:
        unique_words = set(words)
        if len(unique_words) / len(words) < 0.3:  # Too repetitive
            return False
    
    return True

def extract_content_with_guaranteed_fallback(url):
    """Extract content with guaranteed meaningful fallback."""
    
    # Add random delay to avoid being blocked
    time.sleep(random.uniform(5, 10))
    
    try:
        # Use multiple approaches for maximum success
        text, soup = try_multiple_approaches(url)
        
        # Check if we got meaningful content
        if text and is_content_meaningful(text):
            logging.info(f"Successfully extracted meaningful content from {url} ({len(text)} chars)")
            return text, soup
        
        # If content is not meaningful, log and use fallback
        if text:
            logging.warning(f"Extracted content from {url} appears garbled or incomplete")
        else:
            logging.warning(f"No content extracted from {url}")
        
        # Generate fallback content
        fallback_data = generate_fallback_content(url)
        fallback_text = f"FALLBACK CONTENT FOR: {url}\n\n"
        fallback_text += "Based on the URL structure and domain, here are the likely modules:\n\n"
        
        for i, module in enumerate(fallback_data['modules'], 1):
            fallback_text += f"{i}. {module['name']}\n"
            fallback_text += f"   Description: {module['description']}\n\n"
        
        fallback_text += f"\nNote: This content was generated as a fallback when direct extraction failed.\n"
        fallback_text += f"The site may have anti-bot protection or require JavaScript rendering.\n"
        fallback_text += f"Consider using Firecrawl API for better results with restricted sites.\n"
        
        logging.info(f"Generated fallback content for {url}")
        return fallback_text, soup
        
    except Exception as e:
        logging.error(f"All extraction methods failed for {url}: {e}")
        
        # Even if everything fails, generate fallback
        fallback_data = generate_fallback_content(url)
        error_text = f"EXTRACTION FAILED FOR: {url}\n\n"
        error_text += f"Error: {str(e)}\n\n"
        error_text += "Generated fallback modules based on URL analysis:\n\n"
        
        for i, module in enumerate(fallback_data['modules'], 1):
            error_text += f"{i}. {module['name']}\n"
            error_text += f"   Description: {module['description']}\n\n"
        
        return error_text, None

def crawl_and_extract(urls, max_depth=1):
    """
    Universal crawler that handles ANY type of website using multiple approaches.
    GUARANTEED to return meaningful content for every URL.
    """
    visited = set()
    docs = {}
    
    def crawl(url, depth):
        if url in visited or depth > max_depth or should_skip_url(url):
            return
        visited.add(url)
        
        logging.info(f"Crawling {url} (depth: {depth})")
        text, soup = extract_content_with_guaranteed_fallback(url)
        docs[url] = text
        
        # Debug: Save HTML if extraction failed and we have soup
        if soup and not text:
            try:
                # Create debug folder if it doesn't exist
                os.makedirs('debug', exist_ok=True)
                
                # Create timestamped debug filename
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                domain = urlparse(url).netloc.replace('.', '_')
                debug_filename = f"debug/debug_{domain}_{timestamp}_depth{depth}.html"
                
                with open(debug_filename, 'w', encoding='utf-8') as f:
                    f.write(str(soup))
                logging.warning(f"Saved debug HTML to {debug_filename}")
            except Exception as e:
                logging.error(f"Could not save debug HTML: {e}")
        
        # Find and crawl links (only if we have meaningful extracted content, not fallback)
        if (soup and depth < max_depth and text and 
            "FALLBACK CONTENT" not in text and "EXTRACTION FAILED" not in text and
            is_content_meaningful(text)):
            links_found = 0
            for a in soup.find_all("a", href=True):
                if links_found >= 3:  # Reduced link limit for efficiency
                    break
                link = urljoin(url, a['href'])
                if (is_valid_url(link) and 
                    urlparse(link).netloc == urlparse(url).netloc and
                    link not in visited and
                    not should_skip_url(link)):
                    crawl(link, depth + 1)
                    links_found += 1

    # Process all URLs - GUARANTEED to return content for each
    for url in urls:
        if is_valid_url(url):
            crawl(url, 0)
        else:
            logging.error(f"Invalid URL: {url}")
            # Even invalid URLs get fallback content
            docs[url] = f"ERROR: Invalid URL format - {url}\n\nPlease check the URL and try again."
    
    return docs
