"""
Playwright Automation Script for Iden Challenge
Extracts product data from a multi-step wizard interface
"""

import json
import os
import time
import re
import shutil
import signal
import logging
from typing import List, Dict, Optional, Set, Any, Iterator, Tuple
from playwright.sync_api import sync_playwright, Page, Browser
from datetime import timedelta, datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
CONFIG = {
    'base_url': 'https://hiring.idenhq.com/',
    'email': 'poovarasan.s@campusuvce.in',
    'password': 'uYzaYo60',
    'session_file': 'session_state.json',
    'output_file': 'products_data.json',
    'backup_dir': 'backups',
    'timeout': 30000,
    'scroll_pause': 1.2,  # Reduced pause time
    'autosave_threshold': 100,
    'progress_update_interval': 3,  # More frequent updates
    'max_scroll_attempts': 100,
    'no_new_threshold': 3,
    'batch_size': 50  # Process cards in batches
}

# Compiled regex patterns for better performance
PATTERNS = {
    'product_id': re.compile(r"ID:\s*(\d+)"),
    'category': re.compile(r"•\s*([^•\n]+)"),
    'inventory': re.compile(r"Inventory\s+(\d+)"),
    'dollar': re.compile(r'\$(\d+\.\d+)'),
    'modified': re.compile(r"Modified\s+([\w\-]+)"),
    'updated': re.compile(r"Updated\s+([\w\s]+(?:days?|hours?|day|hour|about|ago|minutes?)(?:\s+\w+)?)"),
    'category_fallback': re.compile(r"(Books|Toys|Electronics|Health|Clothing|Office|Garden|Sports|Beauty|Home|Kitchen|Automotive)"),
    'progress': re.compile(r"Showing\s+(\d+)\s+of\s+(\d+)"),
    'time_amount': re.compile(r'(\d+)')
}


class ProgressTracker:
    """Track and display progress in terminal"""
    
    __slots__ = ('start_time', 'total_items', 'current_count', 'last_update_time', 
                 'extraction_rate', 'initial_count')
    
    def __init__(self):
        self.start_time = time.time()
        self.total_items = 0
        self.current_count = 0
        self.last_update_time = 0
        self.extraction_rate = 0
        self.initial_count = 0
    
    def set_total(self, total: int) -> None:
        self.total_items = total
    
    def set_initial_count(self, count: int) -> None:
        self.initial_count = count
        self.current_count = count
    
    def update(self, current: int, force: bool = False) -> bool:
        now = time.time()
        self.current_count = current
        
        if not force and now - self.last_update_time < CONFIG['progress_update_interval']:
            return False
        
        elapsed = now - self.start_time
        if elapsed > 0:
            self.extraction_rate = max(0.1, (current - self.initial_count) / (elapsed / 60))
        
        self.last_update_time = now
        return True
    
    def get_progress_str(self) -> str:
        elapsed = time.time() - self.start_time
        elapsed_str = str(timedelta(seconds=int(elapsed)))
        
        # Calculate ETA more efficiently
        if self.total_items > 0 and self.extraction_rate > 0:
            items_remaining = self.total_items - self.current_count
            minutes_remaining = items_remaining / self.extraction_rate
            remaining_str = str(timedelta(seconds=int(minutes_remaining * 60)))
        else:
            remaining_str = "unknown"
        
        # Build progress string efficiently
        if self.total_items > 0:
            percent = self.current_count / self.total_items * 100
            bar_length = 30
            filled_length = int(bar_length * self.current_count / self.total_items)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)
            progress_info = f"[{bar}] {self.current_count}/{self.total_items} ({percent:.1f}%)"
        else:
            progress_info = f"{self.current_count} items"
            
        return (f"Progress: {progress_info} | "
                f"Rate: {self.extraction_rate:.1f} items/min | "
                f"Elapsed: {elapsed_str} | "
                f"Est. remaining: {remaining_str}")


class ProductScraper:
    """Main scraper class for extracting product data"""
    
    def __init__(self):
        self.products: List[Dict[str, str]] = []
        self.page: Optional[Page] = None
        self.browser: Optional[Browser] = None
        self.context = None
        self.processed_ids: Set[str] = set()
        self.progress = ProgressTracker()
        
        os.makedirs(CONFIG['backup_dir'], exist_ok=True)
        self._load_existing_products()
        signal.signal(signal.SIGINT, self.handle_interrupt)
    
    def _load_existing_products(self) -> None:
        """Load existing products from JSON file if it exists"""
        try:
            if os.path.exists(CONFIG['output_file']):
                with open(CONFIG['output_file'], 'r', encoding='utf-8') as f:
                    self.products = json.load(f)
                    self.processed_ids = {p['id'] for p in self.products if 'id' in p}
                    logger.info(f"Loaded {len(self.products)} existing products")
                    self.progress.set_initial_count(len(self.products))
        except Exception as e:
            logger.error(f"Failed to load existing products: {e}")
            if os.path.exists(CONFIG['output_file']):
                backup_name = f"{CONFIG['output_file']}.bak.{int(time.time())}"
                shutil.copy2(CONFIG['output_file'], backup_name)
                logger.info(f"Created backup: {backup_name}")
            self.products = []
    
    def _save_session_state(self) -> None:
        """Save browser session state"""
        try:
            if self.context:
                with open(CONFIG['session_file'], 'w') as f:
                    json.dump(self.context.storage_state(), f)
                logger.info("Session saved")
        except Exception as e:
            logger.error(f"Session save failed: {e}")
    
    def _load_session_state(self) -> Optional[Dict[str, Any]]:
        """Load existing session if available"""
        try:
            if os.path.exists(CONFIG['session_file']):
                with open(CONFIG['session_file'], 'r') as f:
                    logger.info("Using existing session")
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Session load failed: {e}")
        return None
    
    def _wait_and_click(self, selectors: List[str], timeout_per: int = 3000) -> bool:
        """Try to click first visible selector from list"""
        for selector in selectors:
            try:
                element = self.page.locator(selector).first
                element.wait_for(state='visible', timeout=timeout_per)
                element.click()
                logger.info(f"Clicked: {selector}")
                return True
            except Exception:
                continue
        return False
    
    def _is_visible(self, selectors: List[str]) -> bool:
        """Check if any selector is visible"""
        return any(
            self.page.locator(sel).first.is_visible()
            for sel in selectors
            if self._safe_check_visible(sel)
        )
    
    def _safe_check_visible(self, selector: str) -> bool:
        """Safely check if selector is visible"""
        try:
            return self.page.locator(selector).first.is_visible()
        except Exception:
            return False
    
    def login(self) -> bool:
        """Perform login to the application"""
        try:
            logger.info("Starting login...")
            self.page.goto(CONFIG['base_url'], wait_until='networkidle')
            
            # Fill credentials
            email_input = self.page.locator('input[type="email"], input[name*="email"], input[placeholder*="email"]').first
            email_input.wait_for(state='visible', timeout=CONFIG['timeout'])
            email_input.fill(CONFIG['email'])
            
            password_input = self.page.locator('input[type="password"]').first
            password_input.wait_for(state='visible', timeout=CONFIG['timeout'])
            password_input.fill(CONFIG['password'])
            
            # Submit
            self.page.locator('button:has-text("Sign in"), button[type="submit"]').first.click()
            self.page.wait_for_load_state('networkidle')
            
            # Verify login
            try:
                self.page.wait_for_selector('button:has-text("Launch Challenge")', timeout=10000)
                logger.info("Login successful!")
                self._save_session_state()
                return True
            except:
                logger.error("Login failed")
                return False
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
    
    def navigate_wizard(self) -> bool:
        """Navigate through the wizard steps"""
        try:
            logger.info("Navigating wizard...")
            self.page.wait_for_load_state('domcontentloaded')

            # Check if already at destination
            if self._is_visible(['text="Product Inventory"', 'text=/Showing\\s+\\d+\\s+of\\s+\\d+/']):
                logger.info("Already at Product Inventory")
                return True

            # Define navigation sequence
            wizard_steps = [
                ['button:has-text("Launch Challenge")'],
                ['button:has-text("Local Database")'],
                ['button:has-text("All Products")', 'div[role="button"]:has-text("All Products")'],
                ['button:has-text("Table View")'],  # Optional
                ['button:has-text("View Products")']
            ]
            
            fallback_buttons = ['button:has-text("Next")', 'button:has-text("Continue")', 'button:has-text("Proceed")']

            for attempt in range(CONFIG['max_scroll_attempts']):
                # Check if we've reached the destination
                if self._is_visible(['text="Product Inventory"', 'text=/Showing\\s+\\d+\\s+of\\s+\\d+/']):
                    logger.info("Reached Product Inventory")
                    return True

                # Try wizard steps
                clicked = False
                for step_buttons in wizard_steps:
                    if self._wait_and_click(step_buttons):
                        clicked = True
                        break
                
                # Try fallback buttons
                if not clicked:
                    clicked = self._wait_and_click(fallback_buttons)
                
                if clicked:
                    self.page.wait_for_load_state('networkidle')
                    time.sleep(0.5)
                else:
                    # Trigger UI updates
                    self.page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
                    time.sleep(0.5)

            logger.error("Wizard navigation failed")
            return False

        except Exception as e:
            logger.error(f"Wizard error: {e}")
            return False
    
    def handle_interrupt(self, sig, frame) -> None:
        """Handle Ctrl+C gracefully"""
        logger.warning("⚠️ Interrupted! Saving progress...")
        
        if self.progress.update(len(self.products), force=True):
            logger.info(self.progress.get_progress_str())
        
        # Save with backup
        backup_file = os.path.join(CONFIG['backup_dir'], f"products_backup_{int(time.time())}.json")
        self._save_products_to_file(backup_file)
        self._save_products_to_file(CONFIG['output_file'])
        
        logger.info("Data saved successfully. Exiting.")
        if self.browser:
            self.browser.close()
        exit(0)

    def _parse_relative_time(self, time_str: str) -> Optional[timedelta]:
        """Parse relative time strings efficiently"""
        number_match = PATTERNS['time_amount'].search(time_str)
        if not number_match:
            return None
            
        amount = int(number_match.group(1))
        
        # Use more efficient string matching
        lower_str = time_str.lower()
        if 'day' in lower_str:
            return timedelta(days=amount)
        elif 'hour' in lower_str:
            return timedelta(hours=amount)
        elif 'minute' in lower_str:
            return timedelta(minutes=amount)
        return None

    def _parse_product_card(self, card_text: str) -> Optional[Dict[str, str]]:
        """Parse a single product card efficiently"""
        # Quick validation
        if not card_text or "Iden Challenge" in card_text or "Showing" in card_text:
            return None
        
        lines = card_text.splitlines()
        if not lines:
            return None
            
        # Extract ID first (most important validation)
        id_match = PATTERNS['product_id'].search(card_text)
        if not id_match:
            return None
            
        pid = id_match.group(1)
        if pid in self.processed_ids:
            return None
        
        # Validate numeric ID
        try:
            int(pid)
        except ValueError:
            return None
        
        # Extract other fields using pre-compiled patterns
        name = lines[0].strip()
        
        # Category extraction with fallback
        category = "Unknown"
        category_match = PATTERNS['category'].search(card_text)
        if category_match:
            category = category_match.group(1).strip()
        else:
            fallback_match = PATTERNS['category_fallback'].search(card_text)
            if fallback_match:
                category = fallback_match.group(0)
        
        # Extract numeric fields
        inventory_match = PATTERNS['inventory'].search(card_text)
        inventory = inventory_match.group(1) if inventory_match else "0"
        
        # Skip invalid entries
        if inventory == "Showing":
            return None
            
        dollar_match = PATTERNS['dollar'].search(card_text)
        cost = f"${dollar_match.group(1)}" if dollar_match else "$0.00"
        
        modified_match = PATTERNS['modified'].search(card_text)
        modified = modified_match.group(1) if modified_match else "Unknown"
        
        updated_match = PATTERNS['updated'].search(card_text)
        updated = updated_match.group(1).strip() if updated_match else "Unknown"
        
        return {
            "id": pid,
            "name": name,
            "category": category,
            "inventory": inventory,
            "cost": cost,
            "modified": modified,
            "updated": updated
        }

    def _get_progress_info(self) -> Tuple[Optional[int], Optional[int]]:
        """Get current progress from page"""
        try:
            text = self.page.locator('text=/Showing.*of.*products/').first.inner_text(timeout=1000)
            progress_match = PATTERNS['progress'].search(text)
            if progress_match:
                return int(progress_match.group(1)), int(progress_match.group(2))
        except Exception:
            pass
        return None, None

    def _process_card_batch(self, cards: List) -> Iterator[Dict[str, str]]:
        """Process a batch of cards and yield valid products"""
        for card in cards:
            try:
                card_text = card.inner_text().strip()
                product = self._parse_product_card(card_text)
                if product:
                    yield product
            except Exception:
                continue

    def extract_product_data(self) -> List[Dict[str, str]]:
        """Extract product data with optimized scrolling and batch processing"""
        try:
            logger.info("Extracting product data...")
            newly_added = 0
            
            self.page.wait_for_selector('text="Product Inventory"', timeout=CONFIG['timeout'])
            time.sleep(1)

            # Get initial total count
            _, total = self._get_progress_info()
            if total:
                self.progress.set_total(total)
                logger.info(f"Total products: {total}")
            else:
                self.progress.set_total(400)  # Fallback estimate

            logger.info(self.progress.get_progress_str())

            scroll_attempts = 0
            last_count = len(self.products)
            no_new_count = 0
            adaptive_scroll = 1.0

            while scroll_attempts < CONFIG['max_scroll_attempts']:
                # Get all product cards in current view
                product_cards = self.page.locator('div:has-text("ID:")').all()
                
                # Process cards in batches for better memory usage
                cards_processed = 0
                for product in self._process_card_batch(product_cards):
                    self.products.append(product)
                    self.processed_ids.add(product["id"])
                    newly_added += 1
                    cards_processed += 1

                    # Update progress
                    if self.progress.update(len(self.products)):
                        logger.info(self.progress.get_progress_str())

                    # Autosave
                    if newly_added % CONFIG['autosave_threshold'] == 0:
                        logger.info(f"Autosaving after {newly_added} new items...")
                        self._save_products_to_file(CONFIG['output_file'])

                # Check for completion
                current_count = len(self.products)
                if current_count == last_count:
                    no_new_count += 1
                    if no_new_count >= CONFIG['no_new_threshold']:
                        logger.info("No new products found, ending extraction")
                        break
                else:
                    no_new_count = 0
                    last_count = current_count
                    # Adjust scroll speed based on cards found
                    adaptive_scroll = min(1.0, max(0.3, 1.0 - cards_processed / 30))

                # Check progress indicator
                shown, total = self._get_progress_info()
                if shown and total:
                    if total != self.progress.total_items:
                        self.progress.set_total(total)
                    if shown >= total:
                        logger.info(f"All {total} products loaded")
                        break

                # Optimized scrolling
                try:
                    self.page.evaluate(f"window.scrollBy(0, window.innerHeight * {adaptive_scroll})")
                    time.sleep(CONFIG['scroll_pause'])
                    self.page.keyboard.press("PageDown")
                except Exception as e:
                    logger.warning(f"Scroll error: {e}")
                
                scroll_attempts += 1

            # Final progress update
            if self.progress.update(len(self.products), force=True):
                logger.info(self.progress.get_progress_str())

            logger.info(f"Extraction complete! Total: {len(self.products)} (new: {newly_added})")
            return self.products

        except Exception as e:
            logger.error(f"Extraction error: {e}")
            if self.products:
                self._save_products_to_file(CONFIG['output_file'])
            return self.products
    
    def _save_products_to_file(self, filename: str) -> None:
        """Save products to file with atomic write"""
        if not self.products:
            logger.warning("No products to save")
            return
            
        try:
            # Create backup if saving to main file
            if filename == CONFIG['output_file'] and os.path.exists(filename):
                backup_path = os.path.join(CONFIG['backup_dir'], f"{os.path.basename(filename)}.bak")
                shutil.copy2(filename, backup_path)
            
            # Sort products by ID for consistency
            sorted_products = sorted(
                self.products, 
                key=lambda p: int(p['id']) if p['id'].isdigit() else 9999999
            )
            
            # Atomic write using temp file
            temp_file = f"{filename}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(sorted_products, f, indent=2, ensure_ascii=False)
                
            shutil.move(temp_file, filename)
            logger.info(f"Saved {len(self.products)} products to {filename}")
        except Exception as e:
            logger.error(f"Save failed: {e}")
    
    def _generate_summary_stats(self) -> None:
        """Generate and log summary statistics"""
        if not self.products:
            return
            
        # Category distribution
        categories = {}
        update_times = {}
        
        for product in self.products:
            # Count categories
            cat = product.get('category', 'Unknown')
            categories[cat] = categories.get(cat, 0) + 1
            
            # Count update times
            update = product.get('updated', 'Unknown')
            key = update if update != 'Unknown' else 'Unknown time'
            update_times[key] = update_times.get(key, 0) + 1
        
        logger.info("Product counts by category:")
        for cat, count in sorted(categories.items()):
            logger.info(f"  {cat}: {count}")
            
        logger.info("Update time distribution:")
        for time_frame, count in sorted(update_times.items()):
            logger.info(f"  {time_frame}: {count}")
    
    def run(self) -> None:
        """Main execution method"""
        start_time = time.time()
        with sync_playwright() as p:
            try:
                logger.info("Launching browser...")
                self.browser = p.chromium.launch(
                    headless=False,
                    args=['--disable-blink-features=AutomationControlled']
                )
                
                # Setup context with session
                session_state = self._load_session_state()
                self.context = (self.browser.new_context(storage_state=session_state) 
                               if session_state else self.browser.new_context())
                
                self.page = self.context.new_page()
                self.page.set_default_timeout(CONFIG['timeout'])
                
                # Navigate and check login status
                self.page.goto(CONFIG['base_url'], wait_until='networkidle')
                need_login = not self._is_visible(['button:has-text("Launch Challenge")'])
                
                if need_login:
                    if not self.login():
                        raise Exception("Login failed")
                else:
                    logger.info("Already logged in!")
                
                # Navigate wizard and extract data
                if not self.navigate_wizard():
                    raise Exception("Wizard navigation failed")
                
                products = self.extract_product_data()
                
                # Save and summarize results
                if products:
                    self._save_products_to_file(CONFIG['output_file'])
                    elapsed = time.time() - start_time
                    logger.info(f"✅ Completed in {elapsed:.1f} seconds!")
                    self._generate_summary_stats()
                else:
                    logger.warning("No products extracted")
                
            except Exception as e:
                logger.error(f"Execution error: {e}")
                if self.products:
                    backup_file = os.path.join(CONFIG['backup_dir'], f"products_error_{int(time.time())}.json")
                    self._save_products_to_file(backup_file)
                    logger.info(f"Saved error backup: {backup_file}")
                raise
            finally:
                if self.browser:
                    self.browser.close()


def main():
    """Main entry point"""
    scraper = ProductScraper()
    scraper.run()


if __name__ == "__main__":
    main()