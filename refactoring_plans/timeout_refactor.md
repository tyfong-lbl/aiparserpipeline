```python
async def initialize(self):
    self.playwright = await async_playwright().start()
    self.browser = await self.playwright.chromium.launch(
        headless=True,
        args=[
            '--disable-gpu', 
            '--disable-dev-shm-usage', 
            '--no-sandbox', 
            '--disable-setuid-sandbox',
            '--disable-features=IsolateOrigins,site-per-process'
        ]
    )

async def set_realistic_browser(self, page):
    await page.set_extra_http_headers({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5'
    })
    await page.set_viewport_size({"width": 1920, "height": 1080})

async def select_article_to_api(self, url:str, include_url:bool=True, avg_pause=0):
    page = None
    retries = 2
    
    for attempt in range(retries + 1):
        try:
            page = await self.browser.new_page()
            await self.set_realistic_browser(page)
            
            # Try different wait strategies on different attempts
            wait_until = "domcontentloaded" if attempt > 0 else "load"
            timeout = 45000  # 45 seconds
            
            response = await page.goto(url, timeout=timeout, wait_until=wait_until)
            
            if not response:
                logger.warning(f"No response received for URL: {url} (attempt {attempt+1}/{retries+1})")
                if attempt < retries:
                    await page.close()
                    await asyncio.sleep(2)
                    continue
                return None
                
            if response.status >= 400:
                logger.error(f"HTTP error {response.status} for URL: {url}")
                return None
                
            # Wait for content to stabilize
            await asyncio.sleep(2)
            
            # Try to bypass cookie banners or popups
            try:
                for selector in ['button:has-text("Accept")', 'button:has-text("Accept All")', 
                                'button:has-text("I Agree")', '.cookie-accept', '.consent-accept']:
                    if await page.query_selector(selector):
                        await page.click(selector)
                        await asyncio.sleep(1)
                        break
            except Exception as e:
                logger.debug(f"Error handling cookie banner: {e}")
            
            # Extract content with fallbacks
            title = await page.title()
            text = ""
            
            # Try multiple content extraction methods
            try:
                text = await page.evaluate('() => document.body.innerText')
                
                # If text is too short, try alternative method
                if len(text) < 100:
                    paragraphs = await page.evaluate('''
                        () => Array.from(document.querySelectorAll('p, h1, h2, h3, h4, h5, h6, li'))
                            .filter(el => el.offsetParent !== null)
                            .map(el => el.innerText.trim())
                    ''')
                    text = '\n\n'.join(paragraphs)
            except Exception as e:
                logger.error(f"Error extracting text: {e}")
                if attempt < retries:
                    await page.close()
                    await asyncio.sleep(2)
                    continue
                text = "Error extracting text content"
            
            fulltext = f"{title}.\n\n{text}"
            
            # Process the extracted content
            response_content = self.get_api_response(fulltext=fulltext)
            if response_content is None:
                logger.error("No response content from API")
                return None
                
            stripped = self.strip_markdown(response_content)
            try:
                data = json.loads(stripped)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                logger.error(f"Raw content: {stripped[:200]}...")
                return None
            
            tagged_data = {url: data} if include_url else data
            
            if avg_pause > 0:
                pause = abs(np.random.normal(avg_pause, avg_pause/2))
                await asyncio.sleep(pause)
                
            return tagged_data
            
        except Exception as e:
            logger.error(f"Error processing article at {url} (attempt {attempt+1}/{retries+1}): {e}")
            if attempt < retries:
                logger.info(f"Retrying URL: {url}")
                await asyncio.sleep(2)
            else:
                return None
        finally:
            if page and not page.is_closed():
                await page.close()

async def debug_url(self, url):
    """Debug method to save screenshot and HTML of problematic URL"""
    page = None
    try:
        page = await self.browser.new_page()
        await self.set_realistic_browser(page)
        
        logger.info(f"Debug: Attempting to navigate to: {url}")
        response = await page.goto(url, timeout=30000, wait_until="domcontentloaded")
        
        if not response:
            logger.error(f"Debug: No response for URL: {url}")
            return
            
        logger.info(f"Debug: Response status: {response.status}")
        
        # Save screenshot and HTML
        timestamp = int(time.time())
        debug_dir = Path("debug_output")
        debug_dir.mkdir(exist_ok=True)
        
        screenshot_path = debug_dir / f"debug_screenshot_{timestamp}.png"
        html_path = debug_dir / f"debug_html_{timestamp}.html"
        
        await page.screenshot(path=str(screenshot_path), full_page=True)
        html_content = await page.content()
        
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        logger.info(f"Debug: Saved files: {screenshot_path} and {html_path}")
        
    except Exception as e:
        logger.error(f"Debug error for {url}: {e}")
    finally:
        if page and not page.is_closed():
            await page.close()

async def get_responses_for_url(self, url) -> list:
    """For a particular URL, get all the responses to prompts"""
    prompts = self.get_all_prompts()
    responses = []
    ai_parser = AiParser(api_key=self.api_key,
                         api_url=self.api_url, 
                         model=self.model,
                         prompt=prompts[0],
                         project_name=self.project_name)
    try:
        await ai_parser.initialize()
        
        # First check if URL is accessible
        logger.info(f"Checking accessibility for URL: {url}")
        await ai_parser.debug_url(url)
        
        for i, prompt in enumerate(prompts):
            logger.info(f"Processing prompt {i+1}/{len(prompts)} for URL: {url}")
            ai_parser.prompt = prompt
            article_data = await ai_parser.select_article_to_api(
                url=url, 
                include_url=True,
                avg_pause=1
            )
            
            if article_
                responses.append(article_data)
                logger.info(f"Successfully processed prompt {i+1} for URL: {url}")
            else:
                logger.warning(f"No response for URL {url} with prompt {i+1}")
    
    except Exception as e:
        logger.error(f"Error processing URL {url}: {e}")
        logger.error(traceback.format_exc())
    finally:
        await ai_parser.cleanup()
    
    return responses

async def get_all_url_responses(self) -> dict:
    urls = [url for url in self.url_df.apply(self.extract_urls).dropna()]
    responses = []
    
    for url in tqdm(urls, desc="Getting responses for URLs"):
        try:
            logger.info(f"Processing URL: {url[0]}")
            response = await self.get_responses_for_url(url[0])
            if response:
                responses.append(response)
                logger.info(f"Successfully processed URL: {url[0]}")
            else:
                logger.warning(f"No response for URL: {url[0]}")
        except Exception as e:
            logger.error(f"Error processing URL {url[0]}: {e}")
            logger.error(traceback.format_exc())
    
    return responses

async def consolidate_responses(self) -> pd.DataFrame:
    try:
        data = await self.get_all_url_responses()
        logger.info(f"Received data for {len(data)} URLs")
        
        # Filter out None elements and empty lists
        filtered_data = []
        for item in 
            if item and any(x is not None for x in item):
                filtered_data.append(item)
        
        if not filtered_
            logger.warning("No valid data received from URLs")
            empty_df = pd.DataFrame({'name': [self.project_name], 'url': ['No valid data']})
            return empty_df
            
        try:
            rows = []
            for element in filtered_
                for queries in element:
                    if queries is not None:
                        try:
                            flattened = self.flatten_dict(queries)
                            if flattened:
                                rows.append(flattened)
                        except Exception as e:
                            logger.error(f"Error flattening dict: {e}")
                            continue
            
            if not rows:
                logger.warning("No rows generated after flattening")
                empty_df = pd.DataFrame({'name': [self.project_name], 'url': ['No valid rows']})
                return empty_df
                
            df = pd.DataFrame(rows)
            logger.info(f"DataFrame created. Shape: {df.shape}")
            
            # Add project name
            df['name'] = self.project_name
            
            # Ensure URL column exists
            if 'url' not in df.columns:
                logger.warning("URL column missing from DataFrame")
                df['url'] = "unknown"
            else:
                df['url'] = df['url'].astype(str)
            
            # Process dataframe safely
            try:
                for col in df.columns:
                    df[col] = df[col].astype(str)
                
                grouped_df = df.groupby('url', as_index=False).apply(self.aggregate_data)
                grouped_df.to_csv("temp.csv")
                df_csv = pd.read_csv("temp.csv")
                output_df = df_csv.map(remove_nan)
                return output_df
            except Exception as e:
                logger.error(f"Error during DataFrame processing: {e}")
                logger.error(traceback.format_exc())
                return df  # Return the original dataframe
        except Exception as e:
            logger.error(f"Error processing  {e}")
            logger.error(traceback.format_exc())
            empty_df = pd.DataFrame({'name': [self.project_name], 'url': ['Processing error']})
            return empty_df
    except Exception as e:
        logger.error(f"Unexpected error in consolidate_responses: {e}")
        logger.error(traceback.format_exc())
        empty_df = pd.DataFrame({'name': [self.project_name], 'url': ['Unexpected error']})
        return empty_df

async def process_project(self, project_name: str) -> pd.DataFrame:
    """Process a single project."""
    try:
        if project_name in self.completed_projects:
            self.logger.info(f"Skipping already completed project: {project_name}")
            return pd.DataFrame()

        self.logger.info(f"Processing project: {project_name}")
        project_urls = self.url_df[project_name].dropna()  # Drop NaN values
        
        if project_urls.empty:
            self.logger.warning(f"No URLs found for project: {project_name}")
            return pd.DataFrame()
        
        model_validator = ModelValidator(
            **self.common_params,
            project_name=project_name,
            url_df=project_urls
        )
        
        try:
            self.logger.info(f"Starting consolidation for project: {project_name}")
            df = await model_validator.consolidate_responses()
            
            if df.empty:
                self.logger.warning(f"No data returned for project: {project_name}")
                return pd.DataFrame()
                
            self.project_outputs[project_name] = df
            self.logger.info(f"Successfully processed project: {project_name}")
            self.completed_projects.add(project_name)
            
            try:
                await self._save_checkpoint()
                self.logger.info(f"Checkpoint saved for project: {project_name}")
            except Exception as e:
                self.logger.error(f"Error saving checkpoint: {e}")
                self.logger.error(traceback.format_exc())
                
            return df
        except Exception as e:
            self.logger.error(f"Error processing project {project_name}: {e}")
            self.logger.error(traceback.format_exc())
            return pd.DataFrame()
    except Exception as e:
        self.logger.error(f"Unexpected error processing project {project_name}: {e}")
        self.logger.error(traceback.format_exc())
        return pd.DataFrame()

async def main():
    parser = argparse.ArgumentParser(description="Run multi-project validation")
    parser.add_argument('--keep-checkpoint', action='store_true', help='Keep the checkpoint file after completion')
    parser.add_argument('--timeout', type=int, default=45000, help='Page load timeout in milliseconds (default: 45000)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode with screenshots and HTML dumps')
    args = parser.parse_args()

    logging.info("Starting multi-project validation")
    excel_path = "/Users/TYFong/Desktop/worklogs/project_logs/ai_parser/Solar_Project_Tracker_ITexamples_2022.xlsx"
    api_key = os.environ.get('CYCLOGPT_API_KEY')
    if not api_key:
        logging.error("CYCLOGPT_API_KEY environment variable not set")
        return 1
        
    api_url = "https://api.cborg.lbl.gov"
    model = 'lbl/cborg-chat:latest'
    prompt_directory = Path(__file__).resolve().parent / 'test_prompts'
    output_dir = Path(__file__).resolve().parent / 'results'
    checkpoint_dir = Path(__file__).resolve().parent / 'checkpoints'
    debug_dir = Path(__file__).resolve().parent / 'debug_output'
    checkpoint_filename = 'checkpoint.pkl'
    
    # Create necessary directories
    await create_directory(prompt_directory)
    await create_directory(output_dir)
    await create_directory(checkpoint_dir)
    if args.debug:
        await create_directory(debug_dir)

    checkpoint_path = Path(checkpoint_dir, checkpoint_filename)

    multi_validator = MultiProjectValidator(
        excel_path=excel_path,
        api_key=api_key,
        api_url=api_url,
        model=model,
        prompt_directory=prompt_directory,
        checkpoint_dir=checkpoint_dir
    )

    async with manage_checkpoint(checkpoint_path, args.keep_checkpoint) as (save_complete_event, cleanup_event):
        try:
            await multi_validator.run(output_dir)
            # Wait for the writing to complete
            await multi_validator.writing_complete.wait()
            # Now safe to call save_pickle
            await async_save_pickle(checkpoint_path, save_complete_event)
            # Wait for save_pickle to complete
            await save_complete_event.wait()
        except Exception as e:
            logging.error(f"An error occurred during main execution: {e}")
            logging.error(traceback.format_exc())
            # Don't set cleanup_event, so checkpoint won't be deleted
            return 1  # Indicate error

    logging.info("Main process completed successfully.")
    return 0  # Indicate successful completion

# Global configuration
PAGE_LOAD_TIMEOUT = 45000  # Default timeout in milliseconds
DEBUG_MODE = False  # Default debug mode setting

def configure_page_tracker(timeout=None, debug=None):
    """Configure global settings for page_tracker module"""
    global PAGE_LOAD_TIMEOUT, DEBUG_MODE
    if timeout is not None:
        PAGE_LOAD_TIMEOUT = timeout
    if debug is not None:
        DEBUG_MODE = debug

# Inside main function, after parsing arguments
configure_page_tracker(timeout=args.timeout, debug=args.debug)
