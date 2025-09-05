import time
import os
import sys
from datetime import datetime  # <-- ADDED IMPORT
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
    time.sleep(1)

    print("Navigating to the court reservation page...")
    mijnltvbest_link = wait.until(EC.visibility_of_element_located((By.XPATH, "//a[contains(., 'MIJNLTVBEST')]")))
    actions = ActionChains(driver)
    actions.move_to_element(mijnltvbest_link).perform()
    reserve_link = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Baan reserveren")))
    reserve_link.click()
    time.sleep(1)
    
    print("Waiting for reservation iframe and switching to it...")
    wait.until(EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, "iframe")))
    print("Successfully switched to iframe.")
    
    print("Opening court overview...")
    overview_button_xpath = "//button[contains(., 'Overzicht banen') or contains(., 'Baanoverzicht')]"
    overview_button = wait.until(EC.element_to_be_clickable((By.XPATH, overview_button_xpath)))
    overview_button.click()
    
    # --- NIEUWE FLEXIBELE LOGICA ---
    # Eerst wachten we altijd tot de bekende laad-overlay weg is.
    print("Waiting for any loading overlay to disappear...")
    try:
        # Gebruik een korte wachttijd; de overlay is meestal snel weg.
        WebDriverWait(driver, 5).until(EC.invisibility_of_element_located((By.CLASS_NAME, "MuiBackdrop-root")))
        print("Loading overlay handled.")
    except TimeoutException:
        print("No loading overlay was detected.")

    # Nu proberen we de datumkiezer te openen.
    print("Opening the date picker...")
    try:
        # Poging 1: Klik direct op "Vandaag".
        today_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Vandaag')]")))
        today_button.click()
    except Exception:
        # Poging 2: Als dat mislukt, klik dan eerst nogmaals op "Overzicht banen".
        print("Could not click 'Vandaag', assuming alternate layout and clicking 'Overzicht banen' again.")
        overview_button = wait.until(EC.element_to_be_clickable((By.XPATH, overview_button_xpath)))
        overview_button.click()
        
        # Probeer nu opnieuw op "Vandaag" te klikken.
        print("Retrying to click 'Vandaag'...")
        today_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Vandaag')]")))
        today_button.click()
    # --- EINDE NIEUWE LOGICA ---

    # Dit deel wordt alleen uitgevoerd nadat "Vandaag" succesvol is aangeklikt.
    print("Selecting the day...")
    day_element = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Zondag')]")))
    day_element.click()
    print("Selected 'Zondag'.")
    time.sleep(1)

def find_and_select_slot(driver, wait):
    """
    Finds and selects the first available court slot between 20:30 and 21:30.
    This version handles iframe context, loading spinners, AND scrolls elements
    into view before interacting with them.
    Returns True if a slot is found and clicked, False otherwise.
    """
    try:
        # Step 1: Always re-enter the iframe after any page refresh.
        print("Ensuring focus is within the reservation iframe...")
        driver.switch_to.default_content()
        wait.until(EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, "iframe")))
        print("Successfully focused on iframe.")

        # Step 2: Handle any loading spinners.
        print("Waiting for any loading spinners to disappear...")
        wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, "MuiBackdrop-root")))
        print("Spinners are gone. Page is ready.")

        # --- KEY FIX: SCROLL THE TIME LABELS INTO VIEW ---
        print("Searching for time labels in the HTML (even if off-screen)...")
        # Find the elements by PRESENCE first, as they might not be VISIBLE yet.
        start_time_element = wait.until(EC.presence_of_element_located((By.XPATH, "//span[text()='20:30']")))
        end_time_element = wait.until(EC.presence_of_element_located((By.XPATH, "//span[text()='22:00']")))
        
        print("Time labels found in HTML. Scrolling them into the viewport...")
        # Use JavaScript to scroll the element into the middle of the screen.
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", start_time_element)
        time.sleep(0.5) # A brief pause to allow the scroll to finish smoothly.
        print("Scroll complete. Now getting coordinates.")
        # --- END OF KEY FIX ---

        # Now that the elements are visible, we can safely get their locations.
        start_y = start_time_element.location['y']
        end_y = end_time_element.location['y']
        tolerance = 5
        print(f"Time range y-coordinates defined: Start=~{start_y:.0f}px, End=~{end_y:.0f}px.")

        # Get all court timeline containers
        court_slot_containers = wait.until(EC.visibility_of_all_elements_located((
            By.XPATH, "//div[div/span[contains(text(),'- Padel')]]/following-sibling::div"
        )))

        # Iterate through each court to find a matching slot
        for index, container in enumerate(court_slot_containers[:7]):
            court_name = f"Padel Court {index + 1}"
            print(f"Scanning {court_name}...")

            available_slots = container.find_elements(By.XPATH, ".//button[.//div[contains(@class, 'css-wpwytb')]]")
            if not available_slots:
                continue

            for slot in available_slots:
                slot_y = slot.location['y']
                if (start_y - tolerance) <= slot_y < (end_y - tolerance):
                    print(f"✅ Success! Found an available slot on {court_name} in the target time range.")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", slot)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", slot)
                    driver.switch_to.default_content()
                    return True

        print("❌ No available slots found between 20:30 and 21:30 on any court this attempt.")
        driver.switch_to.default_content()
        return False

    except TimeoutException:
        print("A timeout occurred. The page structure may have changed, or elements didn't load in time.")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        driver.save_screenshot(f'debug_screenshot_{timestamp}.png')
        print(f"Debug screenshot saved as debug_screenshot_{timestamp}.png. Check the screenshot to see what the bot saw.")
        driver.switch_to.default_content()
        return False
    except Exception as e:
        print(f"An unexpected error occurred in find_and_select_slot: {e}")
        driver.switch_to.default_content()
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
    
    players_to_add = ["Luc Brenkman", "Valentijn Wiegmans", "Willem Peters"]
    for player in players_to_add:
        print(f"Adding player: {player}...")
        add_button_xpath = f"//span[text()='{player}']/ancestor::div[contains(@class, 'css-1c1kq07')]/following-sibling::button"
        add_button = wait.until(EC.element_to_be_clickable((By.XPATH, add_button_xpath)))
        add_button.click()
        print(f"Successfully added {player}.")
        time.sleep(2)
        
    print("\nWaiting 3 seconds before confirming reservation...")
    time.sleep(3)
    
    print("Attempting to click 'Reservering bevestigen' button using ActionChains...")
    confirm_button_xpath = "//button[contains(., 'Reservering bevestigen')]"

    # --- NIEUWE ACTIONCHAINS KLIKMETHODE ---
    try:
        # 1. Wacht alleen tot de knop AANWEZIG is, niet per se klikbaar.
        confirm_button = wait.until(EC.presence_of_element_located((By.XPATH, confirm_button_xpath)))
        
        # 2. Creëer een ActionChains object om de muis te simuleren.
        actions = ActionChains(driver)
        
        # 3. Beweeg naar de knop en voer de klik uit.
        actions.move_to_element(confirm_button).click().perform()
        print("ActionChains click sent to confirmation button.")

        # 4. Wacht expliciet op de succesmelding om de reservering te verifiëren.
        print("Waiting for success notification...")
        success_popup_xpath = "//*[contains(text(), 'succesvol')]"
        WebDriverWait(driver, 15).until(EC.visibility_of_element_located((By.XPATH, success_popup_xpath)))
        print("✅ Success notification appeared! Reservation is confirmed.")
        # --- EINDE NIEUWE METHODE ---

    except Exception as e:
        print("The ActionChains click method also failed.")
        raise e # Geef de fout door zodat de main error handler het oppakt.

# --- Main Execution Block ---
if __name__ == "__main__":
    if not EMAIL or not PASSWORD:
        print("Error: EMAIL or PASSWORD environment variables not set.")
        exit()
        
    chrome_options = Options()

    # Opties om botdetectie te omzeilen
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    chrome_options.add_argument(f'user-agent={user_agent}')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Standaard headless opties
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 20)
    
    try:
        print("--- Performing initial login and navigation ---")
        login_and_navigate_to_courts(driver, wait)
        print("--- Login and navigation successful ---")
        slot_found = False
        max_attempts = 100
        for attempt in range(max_attempts):
            print(f"\n--- Starting time slot search: Attempt {attempt + 1}/{max_attempts} ---")
            if find_and_select_slot(driver, wait):
                print("✅ Available time slot found and selected!")
                slot_found = True
                break
            else:
                print("❌ No available slot found on this attempt.")
                if attempt < max_attempts - 1:
                    print("Refreshing the page before the next attempt.")
                    driver.refresh()
                    time.sleep(5)
                    print("Will retry in 15 minutes...")
                    time.sleep(15 * 60)
                else:
                    print("Maximum number of attempts reached.")
        if slot_found:
            print("\n--- Completing reservation ---")
            complete_reservation(driver, wait)
            print("\n🎉 Reservation successfully completed!")
            
            # --- NIEUWE STAP: Screenshot bij succes ---
            print("Taking a screenshot of the successful reservation...")
            driver.save_screenshot('success_screenshot.png')
            print("Screenshot saved as success_screenshot.png")
            # --- EINDE NIEUWE STAP ---
            
        else:
            print("\nCould not find a time slot after all attempts. Exiting.")
            
            # --- NEW: SCREENSHOT WHEN NO SLOTS ARE FOUND ---
            print("Taking a screenshot of the court overview...")
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"no_slot_available_{timestamp}.png"
            driver.save_screenshot(filename)
            print(f"Screenshot saved as {filename}")
            # --- END OF NEW CODE ---
            
    except Exception as e:
        print(f"\n❌ A fatal error occurred: {e}")
        print("The script will now terminate.")
        driver.save_screenshot('fatal_error.png')
        print("Screenshot saved as fatal_error.png")
        sys.exit(1)
        
    finally:
        print("\nClosing browser session.")
        driver.quit()
