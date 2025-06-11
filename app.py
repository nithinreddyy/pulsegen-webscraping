import streamlit as st
import json
import time
import os
from datetime import datetime
from extractor.crawler import crawl_and_extract
from extractor.inference import extract_modules_with_ai
import logging

# Import configuration
try:
    from config.settings import settings
    # Validate configuration on startup
    settings.validate()
except ImportError:
    st.error("Configuration module not found. Please ensure config/settings.py exists.")
    st.stop()
except ValueError as e:
    st.error(f"Configuration error: {e}")
    st.info("Please check your .env file and ensure all required variables are set.")
    st.stop()

# Configure logging to save to logs folder
os.makedirs('logs', exist_ok=True)
log_filename = f"logs/pulse_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()  # Also log to console
    ]
)

# Create debug folder
os.makedirs('debug', exist_ok=True)

# Initialize session state
if 'extraction_results' not in st.session_state:
    st.session_state.extraction_results = None
if 'processing_complete' not in st.session_state:
    st.session_state.processing_complete = False

st.set_page_config(
    page_title=settings.APP_TITLE,
    page_icon="Pulse.jpg",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for Apple-like design
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1.5rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .main-header h1 {
        font-size: 2.5rem;
        font-weight: 300;
        margin: 0;
        letter-spacing: -1px;
    }
    .main-header p {
        font-size: 1rem;
        opacity: 0.9;
        margin: 0.3rem 0 0 0;
    }
    .feature-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
        border: 1px solid #f0f0f0;
        margin: 1rem 0;
    }
    .result-card {
        background: #fafafa;
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    .success-card {
        border-left-color: #4CAF50;
    }
    .warning-card {
        border-left-color: #FF9800;
    }
    .json-container {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .metric-container {
        text-align: center;
        padding: 1rem;
        background: white;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 20px;
        padding: 0.5rem 1.5rem;
        font-weight: 500;
        font-size: 0.9rem;
        transition: all 0.3s ease;
        height: 2.5rem;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# Main header
st.markdown("""
<div class="main-header">
    <h1>Pulse</h1>
    <p>Module Extraction AI Agent</p>
</div>
""", unsafe_allow_html=True)

st.markdown("Extract structured modules and submodules from any documentation website using AI.")

# Sidebar with minimal tips
with st.sidebar:
    st.markdown("### Usage Tips")
    st.markdown("""
    - **Supported Sites**: Any documentation, help center, or support site
    - **Anti-Bot Protection**: System automatically handles blocked sites
    - **Fallback Content**: Always returns meaningful results
    - **Multiple URLs**: Enter one URL per line
    """)
    
    st.markdown("### Example URLs")
    st.markdown("""
    - `https://docs.python.org/3/`
    - `https://help.github.com/`
    - `https://support.discord.com/`
    - `https://help.instagram.com/`
    """)

# Main interface
st.markdown("### Enter Documentation URLs")
urls_input = st.text_area(
    "",
    height=120,
    placeholder="https://support.discord.com/hc/en-us\nhttps://help.instagram.com/\nhttps://docs.python.org/3/",
    label_visibility="collapsed"
)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    # Check if processing is in progress
    is_processing = st.session_state.get('processing_in_progress', False)
    
    if is_processing:
        extract_button = st.button("Processing...", type="secondary", disabled=True, use_container_width=True)
    else:
        extract_button = st.button("Extract Modules", type="primary", use_container_width=True)

if extract_button:
    if urls_input.strip():
        urls = [url.strip() for url in urls_input.strip().split('\n') if url.strip()]
        
        if urls:
            # Set processing state
            st.session_state.processing_in_progress = True
            st.session_state.processing_complete = False
            st.session_state.extraction_results = None
            
            # Force rerun to show disabled button
            st.rerun()
            
        else:
            st.warning("Please enter at least one valid URL")
    else:
        st.warning("Please enter some URLs to process")

# Only process if we're in processing state and haven't completed yet
if (st.session_state.get('processing_in_progress', False) and 
    not st.session_state.get('processing_complete', False) and 
    urls_input.strip()):
    
    urls = [url.strip() for url in urls_input.strip().split('\n') if url.strip()]
    
    if urls:
        # Progress tracking with better estimates
        progress_container = st.container()
        with progress_container:
            st.markdown("### Processing Status")
            
            # Create progress elements
            overall_progress = st.progress(0)
            status_text = st.empty()
            time_text = st.empty()
            
            # Statistics in a clean layout
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                total_metric = st.metric("Total URLs", len(urls))
            with col2:
                processed_metric = st.metric("Processed", 0)
            with col3:
                success_metric = st.metric("Successful", 0)
            with col4:
                fallback_metric = st.metric("Fallback Used", 0)
        
        # Start timing
        start_time = time.time()
        
        try:
            status_text.text("Starting web crawling...")
            
            # Crawl and extract content
            docs = crawl_and_extract(urls, max_depth=1)
            
            overall_progress.progress(0.5)
            status_text.text("Processing content with AI...")
            
            all_results = {}
            processed_count = 0
            success_count = 0
            fallback_count = 0
            
            for i, (url, content) in enumerate(docs.items()):
                try:
                    # Update progress for each URL
                    current_progress = 0.5 + (0.5 * i / len(docs))
                    overall_progress.progress(current_progress)
                    
                    # Calculate elapsed and estimated time
                    elapsed_time = time.time() - start_time
                    if i > 0:
                        avg_time_per_url = elapsed_time / i
                        remaining_urls = len(docs) - i
                        estimated_remaining = avg_time_per_url * remaining_urls
                        time_text.text(f"Elapsed: {int(elapsed_time)}s | Estimated remaining: {int(estimated_remaining)}s")
                    
                    status_text.text(f"Processing {i+1}/{len(docs)}: {url}")
                    
                    # Increment processed count for every URL we attempt
                    processed_count += 1
                    
                    # Extract modules using AI
                    modules_data = extract_modules_with_ai(content, url)
                    
                    # Debug logging
                    if modules_data:
                        logging.info(f"✅ Extracted {len(modules_data)} modules from {url}")
                    else:
                        logging.warning(f"❌ No modules extracted from {url}")
                    
                    # Only store and count results if we got meaningful modules
                    if modules_data and isinstance(modules_data, list) and len(modules_data) > 0:
                        # Store the result
                        all_results[url] = {
                            'content': content,
                            'modules': modules_data,
                            'is_fallback': ("FALLBACK CONTENT" in content or "EXTRACTION FAILED" in content),
                            'content_length': len(content) if content else 0,
                            'has_modules': True
                        }
                        
                        # Only count results that we actually store
                        if all_results[url]['is_fallback']:
                            fallback_count += 1
                        else:
                            success_count += 1
                    else:
                        # Don't count URLs that produce no meaningful results
                        logging.warning(f"Skipping {url} - no meaningful modules extracted")
                    
                    # Update metrics after processing each URL
                    processed_metric.metric("Processed", processed_count)
                    success_metric.metric("Successful", success_count)
                    fallback_metric.metric("Fallback Used", fallback_count)
                    
                except Exception as e:
                    logging.error(f"Error processing {url}: {e}")
                    processed_count += 1
                    # Don't increment success/fallback counts for errors
                    
                    # Update metrics for error case too
                    processed_metric.metric("Processed", processed_count)
                    success_metric.metric("Successful", success_count)
                    fallback_metric.metric("Fallback Used", fallback_count)
            
            # Final progress update
            overall_progress.progress(1.0)
            total_time = int(time.time() - start_time)
            status_text.text(f"Processing complete!")
            time_text.text(f"Total time: {total_time}s")
            
            # Store results in session state
            st.session_state.extraction_results = {
                'all_results': all_results,
                'success_count': success_count,
                'fallback_count': fallback_count,
                'total_time': total_time,
                'total_processed': processed_count,
                'total_urls': len(urls)
            }
            st.session_state.processing_complete = True
            st.session_state.processing_in_progress = False
            
            # Clear progress after a moment
            time.sleep(2)
            progress_container.empty()
            
            # Force rerun to show results
            st.rerun()
            
        except Exception as e:
            st.error(f"An error occurred during processing: {e}")
            logging.error(f"Processing error: {e}")
            st.session_state.processing_in_progress = False

# Display results from session state (persists through reruns)
if st.session_state.processing_complete and st.session_state.extraction_results:
    results_data = st.session_state.extraction_results
    all_results = results_data['all_results']
    success_count = results_data['success_count']
    fallback_count = results_data['fallback_count']
    total_urls = results_data.get('total_urls', 0)
    
    # Display results
    st.markdown("## Extraction Results")
    
    # Check if we have any meaningful results
    if not all_results or len(all_results) == 0:
        st.error(f"No meaningful modules could be extracted from any of the {total_urls} URL(s)")
        st.markdown("""
        ### Possible reasons:
        - The websites have strong anti-bot protection
        - The content is mostly JavaScript-rendered and couldn't be extracted
        - The documentation structure doesn't contain clear modules/sections
        - The content is behind authentication or paywalls
        
        ### Suggestions:
        - Try different documentation URLs (e.g., `/docs`, `/help`, `/support`)
        - Use official API documentation URLs
        - Try sites like GitHub docs, Python docs, or Discord support
        """)
    else:
        # Summary - only show counts for results we actually display
        total_displayed = len(all_results)
        
        if success_count > 0:
            st.success(f"Successfully extracted content from {success_count} URL(s)")
        if fallback_count > 0:
            st.warning(f"Used fallback content for {fallback_count} URL(s)")
        
        skipped_count = total_urls - total_displayed
        if skipped_count > 0:
            st.info(f"Skipped {skipped_count} URL(s) that didn't contain extractable content")
        
        # Verify our counts match what we're displaying
        if total_displayed != (success_count + fallback_count):
            st.error(f"⚠️ Display count mismatch: Showing {total_displayed} results but counted {success_count + fallback_count}")
        
        st.markdown(f"**Displaying {total_displayed} results below:**")
        
        # Results for each URL - Clean JSON display
        for idx, (url, result) in enumerate(all_results.items()):
            st.markdown(f"### Result {idx + 1}")
            
            # Validate result quality for display
            valid_modules = []
            for module in result['modules']:
                if (isinstance(module, dict) and 
                    module.get('module') and len(module.get('module', '')) > 3 and
                    module.get('Description') and len(module.get('Description', '')) > 30 and
                    module.get('Submodules') and isinstance(module.get('Submodules'), dict) and
                    len(module.get('Submodules', {})) >= 1):
                    valid_modules.append(module)
            
            # Determine quality status
            is_high_quality = len(valid_modules) >= 1 and not result['is_fallback']
            is_medium_quality = len(valid_modules) >= 1 and result['is_fallback']
            
            # URL and status in a clean card
            if is_high_quality:
                card_class = "success-card"
                status_text = "High Quality Extraction"
            elif is_medium_quality:
                card_class = "warning-card"
                status_text = "Medium Quality (Fallback Content)"
            else:
                card_class = "warning-card"
                status_text = "Low Quality Extraction"
            
            st.markdown(f"""
            <div class="result-card {card_class}">
                <h4>{url}</h4>
                <p><strong>Status:</strong> {status_text}</p>
                <p><strong>Content Length:</strong> {result['content_length']} characters</p>
                <p><strong>Modules Found:</strong> {len(result['modules'])} total, {len(valid_modules)} high quality</p>
            </div>
            """, unsafe_allow_html=True)
            
            # JSON Output - show all modules but indicate quality
            if result['modules'] and len(result['modules']) > 0:
                # Use valid modules if available, otherwise show all
                modules_to_display = valid_modules if valid_modules else result['modules']
                json_str = json.dumps(modules_to_display, indent=2)
                
                st.markdown("#### JSON Output")
                if not valid_modules:
                    st.warning("⚠️ These results may be of lower quality. Consider trying different URLs.")
                
                st.code(json_str, language='json')
                
                # Download button
                st.download_button(
                    label="Download JSON",
                    data=json_str,
                    file_name=f"modules_{url.replace('https://', '').replace('http://', '').replace('/', '_')}.json",
                    mime="application/json",
                    key=f"download_{idx}",
                    help="Download the extracted modules as JSON file"
                )
            else:
                st.error("No modules could be extracted")
            
            # Optional debug info
            if st.checkbox(f"Show Debug Info", key=f"debug_{idx}"):
                st.markdown("#### Debug Information")
                col1, col2 = st.columns(2)
                with col1:
                    st.text(f"URL: {url}")
                    st.text(f"Content Length: {result['content_length']}")
                    st.text(f"Is Fallback: {result['is_fallback']}")
                    st.text(f"Module Count: {len(result['modules'])}")
                    st.text(f"Valid Module Count: {len(valid_modules)}")
                with col2:
                    if result['content']:
                        st.text_area(
                            "Raw Content (first 1000 chars):", 
                            result['content'][:1000], 
                            height=200,
                            key=f"debug_content_{idx}"
                        )
            
            st.markdown("---")
        
        # Download all results - only if we have results
        if all_results:
            st.markdown("### Download All Results")
            
            # Create clean summary
            summary_results = {}
            for url, result in all_results.items():
                summary_results[url] = {
                    'extraction_status': 'fallback' if result['is_fallback'] else 'success',
                    'content_length': result['content_length'],
                    'modules': result['modules']  # This is now a direct array
                }
            
            all_json = json.dumps(summary_results, indent=2, default=str)
            
            st.download_button(
                label="Download All Results (JSON)",
                data=all_json,
                file_name="pulse_extraction_results.json",
                mime="application/json",
                use_container_width=True,
                help="Download all extraction results as a single JSON file"
            )

# Clean footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; padding: 2rem;'>"
    "<strong>Pulse AI Agent</strong> - Universal documentation module extraction"
    "</div>", 
    unsafe_allow_html=True
)
