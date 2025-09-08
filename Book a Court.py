# --- Imports and setup (no changes) ---
import time
import os
import sys
import datetime # Import datetime for unique filenames
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException, TimeoutException

# Load environment variables
load_dotenv()
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

# --- Function definitions (no changes) ---

def login_and_navigate_to_courts(driver, wait):
    """Performs all steps up to viewing the court schedule for the correct day."""
    print("Navigating to the website...")
    driver.get("https://www.ltvbest.nl/")

    print("Waiting for page body to be present...")
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    print("Page body found.")

    try:
        print("Checking for cookie banner...")
        cookie_wait = WebDriverWait(driver, 5)
        cookie_button_xpath = "//button[contains(., 'Accepteer') or contains(., 'Accept')]"
        cookie_button = cookie_wait.until(EC.element_to_be_clickable((By.XPATH, cookie_button_xpath)))
        print("Cookie banner found. Clicking accept button...")
        cookie_button.click()
        time.sleep(1)
    except TimeoutException:
        print("No cookie banner found, continuing...")

    print("Clicking the login button...")
    login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Inloggen']")))
    login_button.click()
    print("Entering credentials...")
    email_input = wait.until(EC.visibility_of_element_located((By.ID, "login-username")))
    email_input.send_keys(EMAIL)
    password_input = driver.find_element(By.ID, "login-password")
    password_input.send_keys(PASSWORD)
    print("Submitting login form...")
    submit_button = driver.find_element(By.XPATH, "//input[@value='Inloggen']")
    submit_button.click()
    time.sleep(2)

    print("Navigating to the court reservation page...")
    mijnltvbest_link = wait.until(EC.visibility_of_element_located((By.XPATH, "//a[contains(., 'MIJNLTVBEST')]")))
    actions = ActionChains(driver)
    actions.move_to_element(mijnltvbest_link).perform()
    reserve_link = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Baan reserveren")))
    reserve_link.click()
    time.sleep(2)

    print("Waiting for reservation iframe and switching to it...")
    wait.until(EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, "iframe")))
    print("Successfully switched to iframe.")

    print("Opening court overview...")
    overview_button_xpath = "//button[contains(., 'Overzicht banen') or contains(., 'Baanoverzicht')]"
    overview_button = wait.until(EC.element_to_be_clickable((By.XPATH, overview_button_xpath)))
    overview_button.click()

    # --- NIEUWE FLEXIBELE LOGICA ---
    print("Waiting for any loading overlay to disappear...")
    try:
        WebDriverWait(driver, 5).until(EC.invisibility_of_element_located((By.CLASS_NAME, "MuiBackdrop-root")))
        print("Loading overlay handled.")
    except TimeoutException:
        print("No loading overlay was detected.")

    print("Opening the date picker...")
    try:
        today_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Vandaag')]")))
        today_button.click()
    except Exception:
        print("Could not click 'Vandaag', assuming alternate layout and clicking 'Overzicht banen' again.")
        overview_button = wait.until(EC.element_to_be_clickable((By.XPATH, overview_button_xpath)))
        overview_button.click()
        print("Retrying to click 'Vandaag'...")
        today_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Vandaag')]")))
        today_button.click()
    # --- EINDE NIEUWE LOGICA ---

    print("Selecting the day...")
    # Example: Select Saturday. Adjust logic as needed for specific day selection.
    # Note: The original code selected "Zaterdag" then immediately overwrote it by selecting "Donderdag".
    # I'm keeping the last selection ("Donderdag") as per the original script's final state.
    # day_element = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Zaterdag')]"))) # Original line 1
    day_element = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Maandag')]"))) # Original line 2
    day_element.click()
    print("Selected 'Maandag'.")
    time.sleep(2)

def find_and_select_slot(driver, wait):
    """
    Scans court rows for an available 13th time slot.
    Returns True if a slot is found and clicked, False otherwise.
    """
    print("Checking court rows for an available 13th time slot...")
    try:
        # Wait for rows to be present to avoid stale elements after refresh
        court_rows = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[./div/button[contains(@class, 'MuiButtonBase-root')]]")))
        print(f"Found {len(court_rows)} potential court rows.")

        for index, row in enumerate(court_rows[:7]): # Limit check to first 7 courts
            print(f"Checking court row {index + 1}...")
            all_slots_in_row = row.find_elements(By.TAG_NAME, "button")

            if len(all_slots_in_row) >= 13:
                thirteenth_slot = all_slots_in_row[12] # Get the 13th slot (index 12)

                # Check if the slot is available by looking for its specific 'available' class/structure.
                # The XPath ".//div[contains(@class, 'css-wpwytb')]" seems to identify an available slot marker.
                try:
                    thirteenth_slot.find_element(By.XPATH, ".//div[contains(@class, 'css-wpwytb')]")
                    print(f"✅ Found an available slot on row {index + 1}. Clicking it.")
                    driver.execute_script("arguments[0].click();", thirteenth_slot)
                    time.sleep(1) # Wait for click to register
                    return True
                except NoSuchElementException:
                    print(f"Slot on row {index + 1} is not available (occupied or restricted).")
            else:
                print(f"Row {index + 1} does not have enough slots (found {len(all_slots_in_row)}, need at least 13).")
    except TimeoutException:
        print("Could not find court rows. Page might not have loaded correctly or structure changed.")
    except Exception as e:
        print(f"An unexpected error occurred during slot finding: {e}")

    return False # Return False if no slot was found and clicked

def complete_reservation(driver, wait):
    """Adds players and confirms the booking after a slot has been selected."""
    print("Selecting 60 minutes and 4 players...")
    duration_players_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(., '60 min.') and contains(., '4')]")))
    duration_players_button.click()
    time.sleep(1)

    print("\nAdding players to the reservation...")
    player_2_box = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'css-18nf95b') and normalize-space(.//span)='Speler 2']")))
    player_2_box.click()
    time.sleep(2)

    players_to_add = ["Luc Brenkman", "Valentijn Wiegmans", "Quinten Wiegmans"]
    for player in players_to_add:
        print(f"Adding player: {player}...")
        add_button_xpath = f"//span[text()='{player}']/ancestor::div[contains(@class, 'css-1c1kq07')]/following-sibling::button"
        add_button = wait.until(EC.element_to_be_clickable((By.XPATH, add_button_xpath)))
        add_button.click()
        print(f"Successfully added {player}.")
        time.sleep(2) # Wait between adding players to avoid race conditions

    print("\nWaiting 3 seconds before confirming reservation...")
    time.sleep(3)

    print("Attempting to click 'Reservering bevestigen' button using ActionChains...")
    confirm_button_xpath = "//button[contains(., 'Reservering bevestigen')]"

    try:
        confirm_button = wait.until(EC.presence_of_element_located((By.XPATH, confirm_button_xpath)))
        actions = ActionChains(driver)
        actions.move_to_element(confirm_button).click().perform()
        print("ActionChains click sent to confirmation button.")

        print("Waiting for success notification...")
        success_popup_xpath = "//*[contains(text(), 'succesvol')]"
        WebDriverWait(driver, 15).until(EC.visibility_of_element_located((By.XPATH, success_popup_xpath)))
        print("✅ Success notification appeared! Reservation is confirmed.")

    except Exception as e:
        print("The ActionChains click method failed during confirmation.")
        raise e # Re-raise exception to be caught by the main error handler

# --- Main Execution Block ---
if __name__ == "__main__":
    if not EMAIL or not PASSWORD:
        print("Error: EMAIL or PASSWORD environment variables not set.")
        sys.exit(1) # Use sys.exit for a cleaner exit

    chrome_options = Options()
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    chrome_options.add_argument(f'user-agent={user_agent}')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = None # Initialize driver to None for finally block safety
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        wait = WebDriverWait(driver, 20)

        print("--- Performing initial login and navigation ---")
        login_and_navigate_to_courts(driver, wait)
        print("--- Login and navigation successful ---")

        slot_found = False
        max_attempts = 100 # Original value: 100 attempts
        for attempt in range(max_attempts):
            print(f"\n--- Starting time slot search: Attempt {attempt + 1}/{max_attempts} ---")
            if find_and_select_slot(driver, wait):
                print("✅ Available time slot found and selected!")
                slot_found = True
                break # Exit loop on success
            else:
                print(f"❌ No available slot found on attempt {attempt + 1}.")
                if attempt < max_attempts - 1:
                    print("Refreshing page and preparing for next attempt...")
                    driver.refresh()
                    # Wait for a short period after refresh for page elements to settle before next loop iteration
                    time.sleep(5)
                    # The original code had a 15-minute wait here. Keeping it.
                    # Remove or adjust 'time.sleep(15 * 60)' if faster retries are desired.
                    print("Waiting 15 minutes before next retry...")
                    time.sleep(15 * 60) # 15 minutes wait

        if slot_found:
            print("\n--- Completing reservation ---")
            complete_reservation(driver, wait)
            print("\n🎉 Reservation successfully completed!")

            # Screenshot on success
            success_filename = f"success_screenshot_{datetime.datetime.now():%Y%m%d_%H%M%S}.png"
            driver.save_screenshot(success_filename)
            print(f"Screenshot saved as {success_filename}")
        else:
            # --- MODIFICATION START ---
            # Action requested: Take screenshot and stop if no time frame could be selected after all attempts.
            print("\n❌ FINAL RESULT: Could not find an available time slot after all attempts.")
            error_filename = f"failure_no_slot_{datetime.datetime.now():%Y%m%d_%H%M%S}.png"
            driver.save_screenshot(error_filename)
            print(f"Screenshot of final page state saved as {error_filename}.")
            print("Exiting script.")
            # --- MODIFICATION END ---

    except Exception as e:
        print(f"\n❌ A fatal, unexpected error occurred: {e}")
        print("The script will now terminate.")
        if driver:
            # Screenshot on fatal crash/exception
            fatal_error_filename = f"fatal_error_{datetime.datetime.now():%Y%m%d_%H%M%S}.png"
            driver.save_screenshot(fatal_error_filename)
            print(f"Screenshot saved as {fatal_error_filename}")
        sys.exit(1) # Exit with error code

    finally:
        if driver:
            print("\nClosing browser session.")
            driver.quit()
