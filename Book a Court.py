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
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException

# Load environment variables
load_dotenv()
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

# These will be provided by the GitHub Actions workflow.
TARGET_DAY = os.getenv("TARGET_DAY")
TARGET_TIME = os.getenv("TARGET_TIME")

# --------- Custom Exceptions ----------
class NavigationError(Exception): ...
class SlotSearchError(Exception): ...
class ReservationError(Exception): ...

# --------- Utility helpers ----------
def wait_for_page_ready(driver, timeout=20):
    """Waits for full page load and a visible body."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        return True
    except TimeoutException:
        print("⚠️ Page did not reach readyState 'complete' in time.")
        return False

def safe_click_js(driver, element):
    driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'nearest'});", element)
    time.sleep(0.15)
    driver.execute_script("arguments[0].click();", element)

def screenshot(driver, prefix):
    fname = f"{prefix}_{datetime.datetime.now():%Y%m%d_%H%M%S}.png"
    try:
        driver.save_screenshot(fname)
        print(f"📸 Saved screenshot: {fname}")
    except Exception as e:
        print(f"⚠️ Could not save screenshot: {e}")
    return fname

def _open_court_overview_and_day(driver, wait):
    """
    Re-enters the iframe, opens court overview, hits 'Vandaag', and selects TARGET_DAY.
    Must be called after any full page refresh.
    """
    try:
        driver.switch_to.default_content()
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, "iframe")))
        print("✅ Switched to reservation iframe.")

        overview_button_xpath = "//button[contains(., 'Overzicht banen') or contains(., 'Baanoverzicht')]"
        overview_button = wait.until(EC.element_to_be_clickable((By.XPATH, overview_button_xpath)))
        safe_click_js(driver, overview_button)

        # Dismiss potential loading overlay if present
        try:
            WebDriverWait(driver, 5).until(EC.invisibility_of_element_located((By.CLASS_NAME, "MuiBackdrop-root")))
        except TimeoutException:
            pass  # overlay not shown is fine

        # Open date picker via 'Vandaag'
        try:
            today_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Vandaag')]")))
            safe_click_js(driver, today_button)
        except Exception:
            print("↩️ Alternative layout, retrying 'Overzicht banen' then 'Vandaag'...")
            overview_button = wait.until(EC.element_to_be_clickable((By.XPATH, overview_button_xpath)))
            safe_click_js(driver, overview_button)
            today_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Vandaag')]")))
            safe_click_js(driver, today_button)

        print(f"📅 Selecting day: {TARGET_DAY} ...")
        day_xpath = f"//span[contains(text(), '{TARGET_DAY}')]"
        day_element = wait.until(EC.element_to_be_clickable((By.XPATH, day_xpath)))
        safe_click_js(driver, day_element)
        time.sleep(0.6)
    except Exception as e:
        screenshot(driver, "nav_reopen_fail")
        raise NavigationError(f"Failed to (re)open court overview/day: {e}") from e

# --------- Main navigation ----------
def login_and_navigate_to_courts(driver, wait):
    """Performs all steps up to viewing the court schedule for the correct day."""
    try:
        print("Navigating to the website...")
        driver.get("https://www.ltvbest.nl/")
        if not wait_for_page_ready(driver, 20):
            raise NavigationError("Landing page did not fully load in time.")

        # Cookie banner (tolerant)
        try:
            cookie_wait = WebDriverWait(driver, 5)
            cookie_button_xpath = "//button[contains(., 'Accepteer') or contains(., 'Accept')]"
            cookie_button = cookie_wait.until(EC.element_to_be_clickable((By.XPATH, cookie_button_xpath)))
            safe_click_js(driver, cookie_button)
            time.sleep(0.5)
        except TimeoutException:
            pass

        # Login
        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Inloggen']")))
        safe_click_js(driver, login_button)

        email_input = wait.until(EC.visibility_of_element_located((By.ID, "login-username")))
        email_input.clear(); email_input.send_keys(EMAIL)
        password_input = driver.find_element(By.ID, "login-password")
        password_input.clear(); password_input.send_keys(PASSWORD)

        submit_button = driver.find_element(By.XPATH, "//input[@value='Inloggen']")
        safe_click_js(driver, submit_button)
        time.sleep(1.2)

        # Navigate to reservation page
        mijnltvbest_link = wait.until(EC.visibility_of_element_located((By.XPATH, "//a[contains(., 'MIJNLTVBEST')]")))
        ActionChains(driver).move_to_element(mijnltvbest_link).perform()
        reserve_link = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Baan reserveren")))
        safe_click_js(driver, reserve_link)

        if not wait_for_page_ready(driver, 20):
            raise NavigationError("Reservation page did not fully load.")

        # Into iframe and select date
        _open_court_overview_and_day(driver, wait)

    except Exception as e:
        screenshot(driver, "nav_fail")
        if isinstance(e, NavigationError):
            raise
        raise NavigationError(f"Navigation failed: {e}") from e

# --------- Slot search ----------
def find_and_select_slot(driver, wait):
    """
    Finds and clicks the first available slot for the TARGET_TIME.

    RETURNS:
        (bool, str) where str ∈ {'ok','no_time_text','no_clickable','unexpected'}
    """
    try:
        # Ensure list view
        try:
            list_toggle = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='button' and @value='list']")))
            if list_toggle.get_attribute("aria-pressed") in (None, "false"):
                safe_click_js(driver, list_toggle)
                time.sleep(0.5)
        except TimeoutException:
            print("⚠️ List view toggle not found; continuing.")

        # Expand padel courts
        try:
            time.sleep(0.3)
            accordion_buttons = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//button[contains(@class,'MuiAccordionSummary-root')]")))
            padel_courts = [btn for btn in accordion_buttons if "P " in btn.text]
            for btn in padel_courts:
                if btn.get_attribute("aria-expanded") == "false":
                    safe_click_js(driver, btn)
                    time.sleep(0.2)
        except TimeoutException:
            print("⚠️ No court accordions found; continuing.")

        # Find time span
        print(f"🔎 Searching for time slot: '{TARGET_TIME}'...")
        time_slot_xpath = f"//span[normalize-space()='{TARGET_TIME}']"

        try:
            wait.until(EC.presence_of_element_located((By.XPATH, time_slot_xpath)))
        except TimeoutException:
            print(f"❌ No element with the text '{TARGET_TIME}' found on the page.")
            screenshot(driver, "slot_no_time_text")
            return (False, 'no_time_text')

        time_spans = driver.find_elements(By.XPATH, time_slot_xpath)
        print(f"Found {len(time_spans)} potential slots for '{TARGET_TIME}'.")

        for sp in time_spans:
            try:
                slot_container = sp.find_element(By.XPATH, "./ancestor::div[contains(@class,'MuiBox-root') and contains(@class,'css-uu7ccs')]")
                radio_input = slot_container.find_elements(By.XPATH, ".//input[@type='radio']")
                target = radio_input[0] if radio_input else slot_container
                safe_click_js(driver, target)
                time.sleep(0.5)
                print(f"✅ Slot '{TARGET_TIME}' clicked successfully.")
                return (True, 'ok')
            except Exception as e:
                print(f"Could not click this '{TARGET_TIME}' slot: {e}")
                continue

        print(f"❌ No clickable '{TARGET_TIME}' slot found in the list.")
        screenshot(driver, "slot_no_clickable")
        return (False, 'no_clickable')

    except Exception as e:
        screenshot(driver, "slot_unexpected")
        return (False, 'unexpected')

# --------- Reservation ----------
def complete_reservation(driver, wait):
    """Adds players and confirms the booking."""
    try:
        print("Selecting 60 minutes and 4 players...")
        duration_players_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(., '60 min.') and contains(., '4')]")))
        safe_click_js(driver, duration_players_button)
        time.sleep(0.6)

        print("Adding players...")
        player_2_box = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'css-18nf95b') and normalize-space(.//span)='Speler 2']")))
        safe_click_js(driver, player_2_box)
        time.sleep(0.8)

        players_to_add = ["Luc Brenkman", "Valentijn Wiegmans", "Quinten Wiegmans"]
        for player in players_to_add:
            print(f"➕ {player}")
            add_button_xpath = f"//span[text()='{player}']/ancestor::div[contains(@class, 'css-1c1kq07')]/following-sibling::button"
            add_button = wait.until(EC.element_to_be_clickable((By.XPATH, add_button_xpath)))
            safe_click_js(driver, add_button)
            time.sleep(0.8)

        print("Confirming reservation...")
        confirm_button_xpath = "//button[contains(., 'Reservering bevestigen')]"
        confirm_button = wait.until(EC.element_to_be_clickable((By.XPATH, confirm_button_xpath)))
        ActionChains(driver).move_to_element(confirm_button).click().perform()

        success_popup_xpath = "//*[contains(text(), 'succesvol')]"
        WebDriverWait(driver, 15).until(EC.visibility_of_element_located((By.XPATH, success_popup_xpath)))
        print("🎉 Reservation confirmed.")

    except Exception as e:
        screenshot(driver, "confirm_fail")
        raise ReservationError(f"Failed to complete reservation: {e}") from e

# --- Main Execution Block ---
if __name__ == "__main__":
    if not EMAIL or not PASSWORD:
        print("❌ Error: EMAIL or PASSWORD environment variables not set in GitHub Secrets.")
        sys.exit(1)
    if not TARGET_DAY or not TARGET_TIME:
        print("❌ Error: TARGET_DAY or TARGET_TIME not provided by the workflow. Cannot proceed.")
        sys.exit(1)
    print(f"🚀 Starting bot for {TARGET_DAY} at {TARGET_TIME}")

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
        max_attempts = 30  # ~2 minutes with 4s pauses
        for attempt in range(max_attempts):
            print(f"\n--- Time slot search: Attempt {attempt + 1}/{max_attempts} ---")
            ok, reason = find_and_select_slot(driver, wait)
            if ok:
                slot_found = True
                break

            # Refresh logic (with proper waits + iframe re-entry every time)
            if attempt < max_attempts - 1:
                if reason == 'no_clickable':
                    print("🔁 No clickable slot. Refreshing and re-opening selection...")
                elif reason == 'no_time_text':
                    print("🔁 Time text not found (UI not ready?). Refreshing...")
                else:
                    print("🔁 Unexpected slot error. Refreshing...")

                driver.refresh()
                wait_for_page_ready(driver, 20)
                time.sleep(1.0)
                try:
                    _open_court_overview_and_day(driver, wait)
                except NavigationError as e:
                    print(f"⚠️ Recover navigation after refresh failed: {e}")
                    screenshot(driver, "nav_recover_fail")
                    continue
                time.sleep(1.0)

        if slot_found:
            print("\n--- Completing reservation ---")
            complete_reservation(driver, wait)
            success_filename = screenshot(driver, "success")
            print("✅ Done.")
        else:
            print("\n❌ FINAL RESULT: Could not find an available time slot after all attempts.")
            screenshot(driver, "failure_no_slot")
            sys.exit(1)

    except (NavigationError, ReservationError) as e:
        print(f"\n❌ Controlled error: {e}")
        screenshot(driver, "fatal_controlled")
        sys.exit(1)
    except WebDriverException as e:
        print(f"\n❌ WebDriver error: {e}")
        screenshot(driver, "fatal_webdriver")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected fatal error: {e}")
        screenshot(driver, "fatal_unexpected")
        sys.exit(1)
    finally:
        if driver:
            print("\nClosing browser session.")
            try:
                driver.quit()
            except Exception:
                pass
