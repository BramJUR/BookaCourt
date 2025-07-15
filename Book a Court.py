import time
import os
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

# Load environment variables from a .env file (for local development)
load_dotenv()

# --- Securely Load Login Details ---
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

# --- Helper Functions ---
def add_player(driver, wait, player_name):
    # ... (this function remains the same)
    try:
        print(f"Searching for player: {player_name}...")
        add_button_xpath = f"//span[text()='{player_name}']/ancestor::div[contains(@class, 'css-1c1kq07')]/following-sibling::button"
        add_button = wait.until(EC.element_to_be_clickable((By.XPATH, add_button_xpath)))
        add_button.click()
        print(f"Successfully added {player_name}.")
        time.sleep(1)
        return True
    except (NoSuchElementException, TimeoutException) as e:
        print(f"Could not add player {player_name}. Reason: {e}")
        return False

def reserve_court():
    if not EMAIL or not PASSWORD:
        print("Error: EMAIL or PASSWORD environment variables not set.")
        print("Please ensure you have configured repository secrets in GitHub.")
        return False

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 20)

    try:
        print("Navigating to the website...")
        driver.get("https://www.ltvbest.nl/")
        
        # ✨ --- NIEUWE STAP: Probeer cookies te accepteren --- ✨
        try:
            print("Checking for cookie banner...")
            cookie_wait = WebDriverWait(driver, 5) # Wacht max 5 seconden
            # Deze XPath probeert een knop te vinden die 'Accepteer' of 'Accept' bevat
            cookie_button_xpath = "//button[contains(., 'Accepteer') or contains(., 'Accept')]"
            cookie_button = cookie_wait.until(EC.element_to_be_clickable((By.XPATH, cookie_button_xpath)))
            print("Cookie banner found. Clicking accept button...")
            cookie_button.click()
            time.sleep(1) # Geef de pagina even de tijd
        except TimeoutException:
            print("No cookie banner found, continuing...")
        # --- EINDE NIEUWE STAP ---

        print("Clicking the login button...")
        login_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Inloggen']")))
        login_button.click()

        # ... (rest of your function remains the same) ...
        print("Entering credentials...")
        email_input = wait.until(EC.visibility_of_element_located((By.ID, "login-username")))
        email_input.send_keys(EMAIL)
        password_input = driver.find_element(By.ID, "login-password")
        password_input.send_keys(PASSWORD)
        
        print("Submitting login form...")
        submit_button = driver.find_element(By.XPATH, "//input[@value='Inloggen']")
        submit_button.click()
        time.sleep(2)

        print("Hovering over MIJNLTVBEST to reveal dropdown...")
        mijnltvbest_link = wait.until(EC.visibility_of_element_located((By.XPATH, "//a[contains(., 'MIJNLTVBEST')]")))
        actions = ActionChains(driver)
        actions.move_to_element(mijnltvbest_link).perform()
        
        print("Navigating to the court reservation page...")
        reserve_link = wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "Baan reserveren")))
        reserve_link.click()
        time.sleep(2)

        print("Switching to iframe and clicking 'Overzicht banen'...")
        iframe = wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
        driver.switch_to.frame(iframe)
        
        overview_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Overzicht banen')]")))
        overview_button.click()
        
        print("Opening the date picker...")
        today_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Vandaag')]")))
        today_button.click()
        
        print("Looking for 'Zaterdag'...")
        day_element = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Zaterdag')]")))
        day_element.click()
        print("Selected 'Zaterdag'.")
        time.sleep(2)

        print("Checking court rows for an available 13th time slot...")
        court_rows = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[./div/button[contains(@class, 'MuiButtonBase-root')]]")))
        
        slot_found_and_clicked = False
        for index, row in enumerate(court_rows[:7]):
            print(f"Checking court row {index + 1}...")
            try:
                all_slots_in_row = row.find_elements(By.TAG_NAME, "button")
                if len(all_slots_in_row) >= 13:
                    thirteenth_slot = all_slots_in_row[12]
                    try:
                        thirteenth_slot.find_element(By.XPATH, ".//div[contains(@class, 'css-wpwytb')]")
                        print(f"Found an available slot on row {index + 1}. Clicking it.")
                        driver.execute_script("arguments[0].click();", thirteenth_slot)
                        slot_found_and_clicked = True
                        time.sleep(1)
                        break
                    except NoSuchElementException:
                        print(f"Slot on row {index + 1} is not available.")
            except NoSuchElementException:
                print(f"Could not find slots in row {index + 1}.")
                continue

        if not slot_found_and_clicked:
            raise Exception("Could not find an available time slot.")

        print("Selecting 60 minutes and 4 players...")
        duration_players_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(., '60 min.') and contains(., '4')]")))
        duration_players_button.click()
        time.sleep(1)

        print("\nAdding players to the reservation...")
        player_2_box = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'css-18nf95b') and normalize-space(.//span)='Speler 2']")))
        player_2_box.click()
        time.sleep(2)

        if not add_player(driver, wait, "Luc Brenkman"): raise Exception("Failed to add Luc Brenkman")
        if not add_player(driver, wait, "Valentijn Wiegmans"): raise Exception("Failed to add Valentijn Wiegmans")
        if not add_player(driver, wait, "Willem Peters"): raise Exception("Failed to add Willem Peters")

        print("\nWaiting 3 seconds before confirming reservation...")
        time.sleep(3)
        
        print("Clicking 'Reservering bevestigen' button...")
        confirm_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Reservering bevestigen')]")))
        confirm_button.click()
        time.sleep(5)

        print("\n✅ Reservation successfully confirmed!")
        return True

    except Exception as e:
        print(f"\n❌ An error occurred during the reservation process: {e}")
        # ✨ --- SCREENSHOT AANPASSING --- ✨
        driver.save_screenshot('error_screenshot.png')
        print("Screenshot saved as error_screenshot.png")
        # --- EINDE AANPASSING ---
        return False

    finally:
        print("Closing browser session.")
        driver.quit()

# --- Main Execution Block ---
# ... (this part remains the same)
if __name__ == "__main__":
    max_attempts = 100
    for attempt in range(max_attempts):
        print(f"\n--- Starting reservation attempt {attempt + 1} of {max_attempts} ---")
        
        success = reserve_court()

        if success:
            print("\n🎉 Reservation was successful! The script will now terminate.")
            break
        else:
            print(f"--- Attempt {attempt + 1} failed. ---")
            if attempt < max_attempts - 1:
                wait_time_seconds = 15 * 60
                print(f"Will retry in 15 minutes...")
                time.sleep(wait_time_seconds)
            else:
                print("\nMaximum number of attempts reached. Stopping the script.")
    
    print("\nScript has finished.")
