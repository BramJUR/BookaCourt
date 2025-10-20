# --- Imports and setup ---
# Import the 'time' module for adding delays (pauses) in the script.
import time
# Import the 'os' module to interact with the operating system, used here for getting environment variables.
import os
# Import the 'sys' module for system-specific parameters and functions, used here to exit the script.
import sys
# Import the 'datetime' module to work with dates and times, used for creating unique screenshot filenames.
import datetime
# Import the 'load_dotenv' function to load environment variables from a .env file (for local testing).
from dotenv import load_dotenv
# Import the main 'webdriver' from Selenium, which is the core component that controls the browser.
from selenium import webdriver
# Import 'Options' to configure Chrome's behavior, like running in headless mode.
from selenium.webdriver.chrome.options import Options
# Import 'By' which is used to specify how to find elements on a page (e.g., by XPATH, ID, CSS_SELECTOR).
from selenium.webdriver.common.by import By
# Import 'ActionChains' to perform complex user actions like hovering over menus.
from selenium.webdriver.common.action_chains import ActionChains
# Import 'Service' to manage the WebDriver's browser driver (e.g., chromedriver).
from selenium.webdriver.chrome.service import Service
# Import 'WebDriverWait' to make the script wait for certain conditions to be met before proceeding.
from selenium.webdriver.support.ui import WebDriverWait
# Import 'expected_conditions' (aliased as EC) which defines various conditions to wait for (e.g., element is clickable).
from selenium.webdriver.support import expected_conditions as EC
# Import 'ChromeDriverManager' to automatically download and manage the correct version of chromedriver.
from webdriver_manager.chrome import ChromeDriverManager
# Import specific Selenium exceptions to handle errors gracefully.
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException, ElementClickInterceptedException

# --- Load Environment Variables ---
# Execute the function to load variables from a local .env file if it exists.
load_dotenv()
# Get the user's email from the environment variables (provided by GitHub Actions Secrets).
EMAIL = os.getenv("EMAIL")
# Get the user's password from the environment variables.
PASSWORD = os.getenv("PASSWORD")
# Get the target day for booking from the environment variables (e.g., "Donderdag").
TARGET_DAY = os.getenv("TARGET_DAY")
# Get the target time for booking from the environment variables (e.g., "20:30 - 21:30").
TARGET_TIME = os.getenv("TARGET_TIME")

# --- Custom Exceptions for Clearer Error Handling ---
# Define a custom error for failures during the initial navigation and login process.
class NavigationError(Exception): ...
# Define a custom error for failures specifically within the slot searching logic.
class SlotSearchError(Exception): ...
# Define a custom error for failures during the final steps of adding players and confirming.
class ReservationError(Exception): ...

# --- Utility Helper Functions ---
def wait_for_page_ready(driver, timeout=20):
    """Waits for the browser's document.readyState to be 'complete'."""
    print("  - Waiting for page to be fully loaded...")
    try:
        # Wait until the browser's internal status is 'complete'. This is more reliable than just waiting for an element.
        WebDriverWait(driver, timeout).until(lambda d: d.execute_script("return document.readyState") == "complete")
        # As a second check, also wait for the <body> tag to be present in the HTML.
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        print("  - Page is ready.")
        # Return True if the page loaded successfully.
        return True
    except TimeoutException:
        # If the page doesn't load within the timeout period, print a warning and return False.
        print("⚠️ Page did not reach readyState 'complete' in time.")
        return False

def screenshot(driver, prefix):
    """Takes a screenshot with a descriptive, timestamped filename."""
    # Create a unique filename using the provided prefix (e.g., 'nav_fail') and the current timestamp.
    fname = f"{prefix}_{datetime.datetime.now():%Y%m%d_%H%M%S}.png"
    try:
        # Use Selenium's built-in function to save a screenshot of the current browser view.
        driver.save_screenshot(fname)
        # Confirm that the screenshot was saved.
        print(f"📸 Saved screenshot: {fname}")
    except Exception as e:
        # If saving fails for any reason, print an error message.
        print(f"⚠️ Could not save screenshot: {e}")
    # Return the filename for potential future use.
    return fname

def find_element_with_fallbacks(wait, selectors):
    """Tries a list of selectors in order and returns the first one that finds an element."""
    print("  - Searching for element with multiple fallbacks...")
    # Loop through each selector provided in the list (a list of tuples like (By.XPATH, "//path")).
    for selector_type, path in selectors:
        try:
            # Try to find the element using the current selector.
            print(f"  - Trying selector: {selector_type} = {path}")
            # If found, immediately return the element and stop searching.
            return wait.until(EC.presence_of_element_located((selector_type, path)))
        except TimeoutException:
            # If this selector fails (times out), print a message and let the loop continue to the next one.
            print(f"    - Selector failed.")
            continue
    # If the loop finishes without finding the element with any selector, raise an error.
    raise NoSuchElementException("Element could not be found with any of the provided selectors.")

def smarter_click(driver, wait, element):
    """Tries a 'human-like' click first, then falls back to a more forceful JavaScript click."""
    print(f"  - Performing smart click on element: {element.tag_name}...")
    try:
        # First, explicitly wait for the element to be considered 'clickable' by Selenium.
        clickable_element = wait.until(EC.element_to_be_clickable(element))
        # Attempt a user-like click by hovering over the element and then clicking.
        ActionChains(driver).move_to_element(clickable_element).click().perform()
        print("    - ActionChains click successful.")
    except (TimeoutException, ElementClickInterceptedException) as e:
        # If the standard click fails (e.g., it's blocked by an overlay), print a warning.
        print(f"⚠️ Standard click failed: {e.__class__.__name__}. Falling back to JavaScript click.")
        # Scroll the element into the center of the view.
        driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'nearest'});", element)
        # Wait a very short moment for the scroll to complete.
        time.sleep(0.15)
        # Execute a direct JavaScript click, which can often bypass UI obstructions.
        driver.execute_script("arguments[0].click();", element)
        print("    - JavaScript click successful.")

def is_logged_out(driver):
    """Checks if the main 'Inloggen' (Login) button is visible on the page."""
    print("  - Checking for logged-out state...")
    try:
        # If this element is found, it means we are on a page where logging in is an option.
        driver.find_element(By.XPATH, "//span[text()='Inloggen']")
        print("    - Login button found. Current state is LOGGED OUT.")
        # Return True because the user is logged out.
        return True
    except NoSuchElementException:
        # If the element is not found, we assume the user is still logged in.
        print("    - Login button not found. Current state is LOGGED IN.")
        return False

def _open_court_overview_and_day(driver, wait):
    """Handles the repetitive task of navigating into the iframe and selecting the target day."""
    print("  - Navigating to court overview and selecting day...")
    try:
        # Switch from the main page content back to the default context.
        driver.switch_to.default_content()
        # Wait for the reservation iframe to be available and then switch the driver's focus into it.
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, "iframe")))
        print("    - Switched to reservation iframe.")
        # Find the "Court Overview" button.
        overview_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Overzicht banen')]")))
        # Click the button using our robust click function.
        smarter_click(driver, wait, overview_button)
        try:
            # Wait briefly for any loading overlay (the grayed-out screen) to disappear.
            WebDriverWait(driver, 5).until(EC.invisibility_of_element_located((By.CLASS_NAME, "MuiBackdrop-root")))
        except TimeoutException: pass # It's okay if there's no overlay.
        # Find the "Vandaag" (Today) button to open the date picker.
        today_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Vandaag')]")))
        # Click the button.
        smarter_click(driver, wait, today_button)
        # Find the element for our target day (e.g., "Donderdag").
        print(f"    - Selecting day: {TARGET_DAY}...")
        day_element = wait.until(EC.element_to_be_clickable((By.XPATH, f"//span[contains(text(), '{TARGET_DAY}')]")))
        # Click the target day.
        smarter_click(driver, wait, day_element)
        # Explicitly wait for the court list to start loading, indicating the page has updated.
        print("    - Waiting for court list to appear...")
        wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(@id, 'Accordion-P-1')]")))
        print("    - Court list is ready.")
    except Exception as e:
        # If any step in this critical navigation fails, take a screenshot and raise a specific error.
        screenshot(driver, "nav_reopen_fail")
        raise NavigationError(f"Failed to (re)open court overview/day: {e}") from e

def login_and_navigate_to_courts(driver, wait):
    """Performs the full login and navigation process from start to finish."""
    print("--- Starting Login and Navigation ---")
    try:
        # Navigate to the website's homepage.
        print("  - Navigating to the website...")
        driver.get("https://www.ltvbest.nl/")
        # Wait for the page to be fully loaded before doing anything else.
        if not wait_for_page_ready(driver, 20):
            raise NavigationError("Landing page did not fully load in time.")
        # Try to find and click the cookie banner, but don't fail if it's not there.
        try:
            cookie_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Accepteer')]")))
            smarter_click(driver, wait, cookie_button)
        except TimeoutException: pass
        
        # Find the main login button using a list of possible selectors.
        print("  - Finding login button...")
        login_selectors = [
            (By.XPATH, "//span[text()='Inloggen']"),
            (By.XPATH, "//a[contains(@href, 'login')]") # A fallback selector
        ]
        login_button = find_element_with_fallbacks(WebDriverWait(driver, 10), login_selectors)
        # Click the login button.
        smarter_click(driver, wait, login_button)
        
        # Enter the user's credentials.
        print("  - Entering credentials...")
        email_input = wait.until(EC.visibility_of_element_located((By.ID, "login-username")))
        email_input.clear(); email_input.send_keys(EMAIL)
        password_input = driver.find_element(By.ID, "login-password")
        password_input.clear(); password_input.send_keys(PASSWORD)
        # Find and click the final submit button.
        submit_button = driver.find_element(By.XPATH, "//input[@value='Inloggen']")
        smarter_click(driver, wait, submit_button)
        
        # Navigate through the user menu to the reservation page.
        print("  - Navigating to reservation page...")
        mijnltvbest_link = wait.until(EC.visibility_of_element_located((By.XPATH, "//a[contains(., 'MIJNLTVBEST')]")))
        ActionChains(driver).move_to_element(mijnltvbest_link).perform() # Hover over the menu
        reserve_link = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Baan reserveren")))
        smarter_click(driver, wait, reserve_link) # Click the submenu item
        
        # Wait for the new reservation page to load.
        if not wait_for_page_ready(driver, 20):
            raise NavigationError("Reservation page did not fully load.")
        # Call the helper function to enter the iframe and select the correct day.
        _open_court_overview_and_day(driver, wait)
        print("--- Login and Navigation Successful ---")
    except Exception as e:
        # If anything goes wrong, take a screenshot and raise a specific error.
        screenshot(driver, "nav_fail")
        if isinstance(e, NavigationError): raise
        raise NavigationError(f"Navigation failed: {e}") from e

def find_and_select_slot(driver, wait):
    """Searches for and selects the target time slot."""
    try:
        # Ensure the view is set to 'list' mode for easier searching.
        print("  - Ensuring list view is active...")
        try:
            list_toggle = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='button' and @value='list']")))
            if list_toggle.get_attribute("aria-pressed") in (None, "false"):
                smarter_click(driver, wait, list_toggle)
                time.sleep(0.5)
        except TimeoutException: print("⚠️ List view toggle not found.")
        # Find all the court accordions (P1, P2, etc.) and expand any that are closed.
        print("  - Expanding all Padel court accordions...")
        try:
            accordion_buttons = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//button[contains(@class,'MuiAccordionSummary-root')]")))
            for btn in [b for b in accordion_buttons if "P " in b.text and b.get_attribute("aria-expanded") == "false"]:
                smarter_click(driver, wait, btn)
                time.sleep(0.2)
        except TimeoutException: print("⚠️ No court accordions found.")
        
        # Search for the specific time slot text on the page.
        print(f"  - Searching for time slot: '{TARGET_TIME}'...")
        time_slot_xpath = f"//span[normalize-space()='{TARGET_TIME}']"
        try:
            # Wait for at least one element with the target time to be present.
            wait.until(EC.presence_of_element_located((By.XPATH, time_slot_xpath)))
        except TimeoutException:
            # If no such text is found, take a screenshot and return a failure status.
            screenshot(driver, "slot_no_time_text")
            return (False, 'no_time_text')
        
        # Get all elements that match the time slot text.
        time_spans = driver.find_elements(By.XPATH, time_slot_xpath)
        print(f"  - Found {len(time_spans)} potential slots for '{TARGET_TIME}'.")
        # Loop through each found time slot to find one that is clickable.
        for sp in time_spans:
            try:
                # Find the parent container of the time slot text.
                slot_container = sp.find_element(By.XPATH, "./ancestor::div[contains(@class,'css-uu7ccs')]")
                # The clickable element is either a radio button inside or the container itself.
                radio_input = slot_container.find_elements(By.XPATH, ".//input[@type='radio']")
                target = radio_input[0] if radio_input else slot_container
                # Click the target.
                smarter_click(driver, wait, target)
                print(f"  - ✅ Slot '{TARGET_TIME}' clicked successfully.")
                # If the click succeeds, return a success status.
                return (True, 'ok')
            except Exception: continue # If this specific one fails, try the next one.
        # If the loop finishes and no slot could be clicked, return a failure status.
        screenshot(driver, "slot_no_clickable")
        return (False, 'no_clickable')
    except Exception as e:
        # If an unexpected error occurs, screenshot and return a failure status.
        print(f"  - ❌ Unexpected error in find_and_select_slot: {e}")
        screenshot(driver, "slot_unexpected")
        return (False, 'unexpected')

def complete_reservation(driver, wait):
    """Finalizes the reservation by adding players and confirming."""
    print("--- Completing Reservation ---")
    try:
        # Select the duration and number of players.
        print("  - Selecting 60 minutes and 4 players...")
        duration_players_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(., '60 min.') and contains(., '4')]")))
        smarter_click(driver, wait, duration_players_button)
        # Open the player selection list.
        print("  - Opening player list...")
        player_2_box = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[normalize-space(.//span)='Speler 2']")))
        smarter_click(driver, wait, player_2_box)
        
        # Loop through the list of players to add.
        for player in ["Luc Brenkman", "Valentijn Wiegmans", "Quinten Wiegmans"]:
            print(f"  - Adding player: {player}")
            # Find the "add" button next to the player's name.
            add_button = wait.until(EC.element_to_be_clickable((By.XPATH, f"//span[text()='{player}']/ancestor::div[contains(@class, 'css-1c1kq07')]/following-sibling::button")))
            # Click to add the player.
            smarter_click(driver, wait, add_button)
        
        # Click the final confirmation button.
        print("  - Finding and clicking the final confirmation button...")
        try:
            # First, wait for any final loading overlays to disappear.
            wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, "MuiBackdrop-root")))
        except TimeoutException: pass
        
        # Use a list of fallback selectors to find the confirmation button.
        confirm_selectors = [
            (By.XPATH, "//button[contains(., 'Reservering bevestigen')]"),
            (By.XPATH, "//button[contains(., 'Volgende')]"),
            (By.CSS_SELECTOR, "button.MuiButton-containedPrimary") # A generic fallback
        ]
        confirm_button = find_element_with_fallbacks(wait, confirm_selectors)
        # Click the button.
        smarter_click(driver, wait, confirm_button)

        # Wait for the success pop-up message to appear.
        print("  - Waiting for success notification...")
        wait.until(EC.visibility_of_element_located((By.XPATH, "//*[contains(text(), 'succesvol')]")))
        print("🎉 Reservation confirmed.")
    except Exception as e:
        # If any step fails, take a screenshot and raise a specific error.
        screenshot(driver, "confirm_fail")
        raise ReservationError(f"Failed to complete reservation: {e}") from e

# --- Main Execution Block ---
if __name__ == "__main__":
    # Check if all required environment variables are present.
    if not all([EMAIL, PASSWORD, TARGET_DAY, TARGET_TIME]):
        print("❌ Error: Missing one or more required environment variables.")
        sys.exit(1)
    # Print a startup message to the log.
    print(f"🚀 Starting bot for {TARGET_DAY} at {TARGET_TIME}")
    # Configure Chrome options for running in a server environment (GitHub Actions).
    chrome_options = Options(); chrome_options.add_argument("--headless"); chrome_options.add_argument("--no-sandbox"); chrome_options.add_argument("--disable-dev-shm-usage"); chrome_options.add_argument("--window-size=1920,1080")
    # Initialize the driver variable to None so it exists in the 'finally' block.
    driver = None
    try:
        # Set up the WebDriver service automatically.
        service = Service(ChromeDriverManager().install())
        # Create the WebDriver instance.
        driver = webdriver.Chrome(service=service, options=chrome_options)
        # Set up the default explicit wait time (e.g., 15 seconds).
        wait = WebDriverWait(driver, 15)
        # Run the main login and navigation function.
        login_and_navigate_to_courts(driver, wait)
        # Initialize a flag to track if we've successfully selected a slot.
        slot_found = False
        # Start the main retry loop. It will try up to 30 times.
        for attempt in range(30):
            print(f"\n--- Time slot search: Attempt {attempt + 1}/30 ---")
            # Call the function to find and select a slot.
            ok, reason = find_and_select_slot(driver, wait)
            # If it returns 'ok' as True, we're done.
            if ok:
                slot_found = True
                break # Exit the loop.
            # If the loop is not on its last iteration, attempt to recover.
            if attempt < 29:
                print(f"🔁 Slot search failed (reason: {reason}). Attempting recovery...")
                # --- State-Aware Recovery Logic ---
                # Check if the bot was logged out.
                if is_logged_out(driver):
                    print("‼️ Detected a logout! Attempting to re-login and navigate...")
                    try:
                        # If logged out, try to run the full login process again.
                        login_and_navigate_to_courts(driver, wait)
                    except Exception as e:
                        # If the re-login fails, fall back to a simple page refresh.
                        print(f"⚠️ Re-login attempt failed: {e}. Falling back to page refresh.")
                        driver.refresh()
                else:
                    # If still logged in, the issue is likely a UI glitch, so just refresh.
                    print("  - State appears normal. Refreshing page as a standard recovery...")
                    driver.refresh()
                # --- END of State-Aware Recovery ---
                try:
                    # After any recovery action, wait for the page and re-navigate to the correct day.
                    wait_for_page_ready(driver, 20)
                    _open_court_overview_and_day(driver, wait)
                except NavigationError as e:
                    # If even the recovery navigation fails, log it and continue to the next attempt.
                    print(f"⚠️ Recovery navigation failed: {e}. Continuing to next attempt.")
                    screenshot(driver, "nav_recover_fail")
        # After the loop, check if a slot was ever found.
        if slot_found:
            # If yes, proceed to the final reservation steps.
            complete_reservation(driver, wait)
            # Take a final success screenshot.
            screenshot(driver, "success")
            print("✅ Done.")
        else:
            # If the loop finished without success, print a final failure message.
            print("\n❌ FINAL RESULT: Could not find an available time slot.")
            screenshot(driver, "failure_no_slot")
            # Exit with a non-zero status code to make the GitHub Action fail.
            sys.exit(1)
    except Exception as e:
        # This is a catch-all for any unhandled error during the entire process.
        print(f"\n❌ An unrecoverable error occurred: {e}")
        if driver: screenshot(driver, "fatal_error")
        # Exit with a failure code.
        sys.exit(1)
    finally:
        # This block will run no matter what happens (success or failure).
        if driver:
            # If the driver was successfully created, ensure it's closed to free up resources.
            print("\nClosing browser session.")
            driver.quit()
