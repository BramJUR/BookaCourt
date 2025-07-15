import time
import os
import sys
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

    # Wacht tot de basis van de pagina (de body) geladen is.
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
    print("Switching to iframe and opening court overview...")
    iframe = wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
    driver.switch_to.frame(iframe)
    overview_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Overzicht banen')]")))
    overview_button.click()
    print("Opening the date picker and selecting the day...")
    today_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Vandaag')]")))
    today_button.click()
    day_element = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Zaterdag')]")))
    day_element.click()
    print("Selected 'Zaterdag'.")
    time.sleep(2)

def find_and_select_slot(driver, wait):
    """
    Scans court rows for an available 13th time slot.
    Returns True if a slot is found and clicked, False otherwise.
    """
    print("Checking court rows for an available 13th time slot...")
    try:
        court_rows = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[./div/button[contains(@class, 'MuiButtonBase-root')]]")))
        for index, row in enumerate(court_rows[:7]):
            print(f"Checking court row {index + 1}...")
            all_slots_in_row = row.find_elements(By.TAG_NAME, "button")
            if len(all_slots_in_row) >= 13:
                thirteenth_slot = all_slots_in_row[12]
                try:
                    thirteenth_slot.find_element(By.XPATH, ".//div[contains(@class, 'css-wpwytb')]")
                    print(f"Found an available slot on row {index + 1}. Clicking it.")
                    driver.execute_script("arguments[0].click();", thirteenth_slot)
                    time.sleep(1)
                    return True
                except NoSuchElementException:
                    print(f"Slot on row {index + 1} is not available.")
            else:
                print(f"Row {index + 1} does not have 13 slots.")
    except TimeoutException:
        print("Could not find court rows. Page might not have loaded correctly.")
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
        time.sleep(1)
        
    print("\nWaiting 3 seconds before confirming reservation...")
    time.sleep(3)
    
    print("Clicking 'Reservering bevestigen' button...")
    confirm_button_xpath = "//button[contains(., 'Reservering bevestigen')]"
    
    # 1. Wacht tot de knop aanwezig is in de DOM
    confirm_button = wait.until(EC.presence_of_element_located((By.XPATH, confirm_button_xpath)))
    
    # 2. Scroll de knop naar het midden van het scherm
    driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", confirm_button)
    time.sleep(1) # Kleine pauze voor stabiliteit na het scrollen
    
    # 3. Klik op de knop met JavaScript
    driver.execute_script("arguments[0].click();", confirm_button)
    print("Confirmation click sent.")
    time.sleep(5)

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
        else:
            print("\nCould not find a time slot after all attempts. Exiting.")
    except Exception as e:
        print(f"\n❌ A fatal error occurred: {e}")
        print("The script will now terminate.")
        driver.save_screenshot('fatal_error.png')
        print("Screenshot saved as fatal_error.png")
        sys.exit(1)
    finally:
        print("\nClosing browser session.")
        driver.quit()
