# --- Imports and setup ---
import time
import os
import sys
import datetime
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

# === CHANGE 1: Get target day and time from environment variables ===
# These will be provided by the GitHub Actions workflow.
TARGET_DAY = os.getenv("TARGET_DAY")
TARGET_TIME = os.getenv("TARGET_TIME")
# =================================================================

def login_and_navigate_to_courts(driver, wait):
    """Performs all steps up to viewing the court schedule for the correct day."""
    # This entire function is perfect, except for the last part which we will change.
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
    
    # === CHANGE 2: Use the TARGET_DAY variable to find and click the day ===
    print(f"Selecting the target day: {TARGET_DAY}...")
    day_xpath = f"//span[contains(text(), '{TARGET_DAY}')]"
    day_element = wait.until(EC.element_to_be_clickable((By.XPATH, day_xpath)))
    day_element.click()
    print(f"Selected '{TARGET_DAY}'.")
    # ======================================================================
    time.sleep(2)


def find_and_select_slot(driver, wait):
    """Finds and clicks the first available slot for the TARGET_TIME."""
    try:
        # Steps 1 & 2 (switching to list view and expanding courts) are perfect. No changes needed.
        try:
            list_toggle = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='button' and @value='list']")))
            if list_toggle.get_attribute("aria-pressed") in (None, "false"):
                driver.execute_script("arguments[0].click();", list_toggle)
                time.sleep(0.75)
        except TimeoutException:
            print("⚠️ List view button not found; continuing.")

        try:
            time.sleep(0.5)
            accordion_buttons = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//button[contains(@class,'MuiAccordionSummary-root')]")))
            padel_courts = [btn for btn in accordion_buttons if "P " in btn.text]
            for btn in padel_courts:
                if btn.get_attribute("aria-expanded") == "false":
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                    time.sleep(0.2)
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(0.3)
        except TimeoutException:
            print("⚠️ No court accordions found; continuing.")

        # === CHANGE 3: Use the TARGET_TIME variable to find the slot ===
        print(f"Searching for time slot: '{TARGET_TIME}'...")
        time_slot_xpath = f"//span[normalize-space()='{TARGET_TIME}']"
        # ===============================================================

        try:
            wait.until(EC.presence_of_element_located((By.XPATH, time_slot_xpath)))
        except TimeoutException:
            print(f"❌ No element with the text '{TARGET_TIME}' found on the page.")
            return False

        time_spans = driver.find_elements(By.XPATH, time_slot_xpath)
        print(f"Found {len(time_spans)} potential slots for '{TARGET_TIME}'.")

        for sp in time_spans:
            try:
                # The logic to find the clickable element is great. No changes.
                slot_container = sp.find_element(By.XPATH, "./ancestor::div[contains(@class,'MuiBox-root') and contains(@class,'css-uu7ccs')]")
                radio_input = slot_container.find_elements(By.XPATH, ".//input[@type='radio']")
                target = radio_input[0] if radio_input else slot_container
                
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target)
                time.sleep(0.2)
                driver.execute_script("arguments[0].click();", target)
                time.sleep(0.6)
                print(f"✅ Slot '{TARGET_TIME}' clicked successfully.")
                return True
            except Exception as e:
                print(f"Could not click this '{TARGET_TIME}' slot: {e}")
                continue
        
        print(f"❌ No clickable '{TARGET_TIME}' slot found in the list.")
        return False

    except Exception as e:
        print(f"❌ Unexpected error in find_and_select_slot: {e}")
        return False


def complete_reservation(driver, wait):
    """Adds players and confirms the booking. No changes needed here, it's perfect."""
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
        time.sleep(2)

    print("\nWaiting 3 seconds before confirming reservation...")
    time.sleep(3)

    print("Attempting to click 'Reservering bevestigen' button...")
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
        print("The confirmation click method failed.")
        raise e


# --- Main Execution Block ---
if __name__ == "__main__":
    # === CHANGE 4: Validate inputs and add startup message ===
    if not EMAIL or not PASSWORD:
        print("❌ Error: EMAIL or PASSWORD environment variables not set in GitHub Secrets.")
        sys.exit(1)
    if not TARGET_DAY or not TARGET_TIME:
        print("❌ Error: TARGET_DAY or TARGET_TIME not provided by the workflow. Cannot proceed.")
        sys.exit(1)
    print(f"🚀 Starting bot for {TARGET_DAY} at {TARGET_TIME}")
    # =========================================================

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

    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        wait = WebDriverWait(driver, 20)

        login_and_navigate_to_courts(driver, wait)
        
        slot_found = False
        # === CHANGE 5: Improved retry logic for automation ===
        # A 15-minute wait is too long for a GitHub Action. We'll try more frequently for a shorter period.
        # Let's try 30 times with a 4-second pause (~2 minutes total).
        max_attempts = 30
        for attempt in range(max_attempts):
            print(f"\n--- Starting time slot search: Attempt {attempt + 1}/{max_attempts} ---")
            if find_and_select_slot(driver, wait):
                slot_found = True
                break
            else:
                if attempt < max_attempts - 1:
                    print("Refreshing page and waiting 4 seconds before next attempt...")
                    driver.refresh()
                    time.sleep(4)
        # ====================================================

        if slot_found:
            print("\n--- Completing reservation ---")
            complete_reservation(driver, wait)
            print("\n🎉 Reservation successfully completed!")
            success_filename = f"success_screenshot_{datetime.datetime.now():%Y%m%d_%H%M%S}.png"
            driver.save_screenshot(success_filename)
            print(f"Screenshot saved as {success_filename}")
        else:
            print("\n❌ FINAL RESULT: Could not find an available time slot after all attempts.")
            error_filename = f"failure_no_slot_{datetime.datetime.now():%Y%m%d_%H%M%S}.png"
            driver.save_screenshot(error_filename)
            print("Exiting script with error code to fail the workflow.")
            # === CHANGE 6: Exit with an error to make the GitHub Action fail ===
            sys.exit(1)
            # ===================================================================

    except Exception as e:
        print(f"\n❌ A fatal, unexpected error occurred: {e}")
        if driver:
            fatal_error_filename = f"fatal_error_{datetime.datetime.now():%Y%m%d_%H%M%S}.png"
            driver.save_screenshot(fatal_error_filename)
            print(f"Screenshot saved as {fatal_error_filename}")
        sys.exit(1)

    finally:
        if driver:
            print("\nClosing browser session.")
            driver.quit()
