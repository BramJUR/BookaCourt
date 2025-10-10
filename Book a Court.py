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
    print("Selected 'Donderdag'.")
    time.sleep(2)

def find_and_select_slot(driver, wait):
    """
    Zet eerst de 'lijst weergave' aan, klap alle banen (P1 t/m P7) open,
    en klik daarna op het eerste slot met '20:30 - 21:30'.
    Retourneert True als het slot is gevonden en aangeklikt, anders False.
    """
    try:
        # 1) Schakel naar lijstweergave
        try:
            list_toggle = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[@type='button' and @value='list']")))
            # Alleen klikken als hij nog niet actief is
            aria_pressed = list_toggle.get_attribute("aria-pressed")
            if aria_pressed in (None, "false"):
                driver.execute_script("arguments[0].click();", list_toggle)
                time.sleep(0.75)
        except TimeoutException:
            print("⚠️ Lijstweergave-knop niet gevonden; ga door met huidige weergave.")

        # 2) Klap alle banen (P1 t/m P7) open
        #    We zoeken naar alle accordion-samenvattingen (P 1 ... P 7) en klikken als ze dicht zijn.
        try:
            # even een korte wacht zodat de lijstweergave bouwt
            time.sleep(0.5)
            accordion_buttons = wait.until(EC.presence_of_all_elements_located(
                (By.XPATH, "//button[contains(@class,'MuiAccordionSummary-root') and contains(@id,'Accordion')]")))
            # Filter op P 1 t/m P 7
            filtered = []
            for btn in accordion_buttons:
                try:
                    # Tekst als "P 2 " zit in een child-span; we controleren op 'P ' prefix
                    if "P " in btn.text:
                        filtered.append(btn)
                except Exception:
                    pass

            # Klik alles open dat nog niet open is
            for btn in filtered:
                try:
                    expanded = btn.get_attribute("aria-expanded")
                    if expanded == "false":
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                        time.sleep(0.2)
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.3)
                except Exception as e:
                    print(f"Kon baan-accordion niet openen: {e}")
        except TimeoutException:
            print("⚠️ Geen baan-accordions gevonden; ga verder met zoeken naar tijdslot.")

        # 3) Zoek het eerste slot '20:30 - 21:30' en klik
        #    We zoeken de tijdspan en gaan dan naar de container om het radio-element te klikken.
        try:
            # Wacht tot er in de lijst items verschijnen
            wait.until(EC.presence_of_element_located(
                (By.XPATH, "//span[normalize-space()='20:30 - 21:30']")))
        except TimeoutException:
            print("❌ Geen element met de tekst '20:30 - 21:30' gevonden.")
            return False

        time_spans = driver.find_elements(By.XPATH, "//span[normalize-space()='20:30 - 21:30']")
        print(f"Gevonden tijdvakken met '20:30 - 21:30': {len(time_spans)}")

        for sp in time_spans:
            try:
                # Container van één slot (zoals je voorbeeld met css-uu7ccs)
                slot_container = sp.find_element(
                    By.XPATH,
                    "./ancestor::div[contains(@class,'MuiBox-root')][contains(@class,'css-uu7ccs')]"
                )

                # Zoek het radio-klikdoel binnen dit slot
                # 1) Probeer direct de PrivateSwitchBase/input
                radio_input_candidates = slot_container.find_elements(
                    By.XPATH, ".//input[@type='radio']"
                )

                # 2) Back-up: klik de zichtbare radio wrapper (span met MuiRadio-root)
                radio_span_candidates = slot_container.find_elements(
                    By.XPATH, ".//span[contains(@class,'MuiRadio-root') or contains(@class,'PrivateSwitchBase-root')]"
                )

                target = None
                if radio_input_candidates:
                    target = radio_input_candidates[0]
                elif radio_span_candidates:
                    target = radio_span_candidates[0]
                else:
                    # Als er geen radio te vinden is, proberen we als back-up het hele slot te klikken
                    target = slot_container

                # Scroll in beeld en klik via JS (stabieler dan gewone .click bij overlay issues)
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target)
                time.sleep(0.2)
                try:
                    driver.execute_script("arguments[0].click();", target)
                except Exception:
                    # Als JS-click weigert, probeer ActionChains
                    actions = ActionChains(driver)
                    actions.move_to_element(target).click().perform()

                time.sleep(0.6)  # heel even wachten zodat selectie kan registreren
                print("✅ Slot '20:30 - 21:30' aangeklikt.")
                return True

            except Exception as e:
                print(f"Kon dit '20:30 - 21:30' slot niet aanklikken: {e}")
                continue

        print("❌ Geen klikbaar '20:30 - 21:30' slot gevonden in de lijst.")
        return False

    except Exception as e:
        print(f"❌ Onverwachte fout in find_and_select_slot: {e}")
        return False


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
