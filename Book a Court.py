import time
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException

# --- CONFIGURATION ---
# Load environment variables from your .env file
load_dotenv()
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

# Set your reservation preferences here
TARGET_DAY = "Zondag"  # The day you want to book (e.g., "Zondag", "Maandag")
TARGET_START_TIME = "20:30" # The earliest time slot you want
# --- END CONFIGURATION ---


def get_driver_and_wait():
    """Initializes and returns the Chrome driver and a WebDriverWait instance."""
    print("DEBUG: Setting up Chrome driver options...")
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
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 20) # 20-second timeout for waits
    print("DEBUG: Chrome driver and wait object initialized.")
    return driver, wait


def login(driver, wait):
    """Handles the initial website login process."""
    print("STEP 1: LOGIN")
    print(" -> Navigating to the website...")
    driver.get("https://www.ltvbest.nl/")
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    try:
        print(" -> Checking for cookie banner...")
        cookie_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Accepteer')]")))
        cookie_button.click()
        print(" -> Cookie banner accepted.")
    except TimeoutException:
        print(" -> No cookie banner found, continuing...")

    print(" -> Clicking the main login button...")
    wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Inloggen']"))).click()
    
    print(" -> Entering credentials...")
    wait.until(EC.visibility_of_element_located((By.ID, "login-username"))).send_keys(EMAIL)
    driver.find_element(By.ID, "login-password").send_keys(PASSWORD)
    driver.find_element(By.XPATH, "//input[@value='Inloggen']").click()
    
    # Confirmation of successful login by finding the "Account" button
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "a.show-account .btn-label")))
    print(" -> Login successful. Account button is visible.")


def navigate_and_select_day(driver, wait, target_day):
    """Navigates to the court overview, handles different initial views, and selects the target day."""
    print("\nSTEP 2: NAVIGATE AND SELECT DAY")
    print(" -> Navigating directly to the reservation page...")
    driver.get("https://www.ltvbest.nl/index.php?page=Afhangen")
    
    print(" -> Waiting for the reservation iframe to be available...")
    wait.until(EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, "iframe")))
    print(" -> Successfully switched focus to iframe.")

    # --- KEY FIX: RESTORED AND IMPROVED FLEXIBLE VIEW HANDLING LOGIC ---
    print(" -> Checking the initial state of the reservation view...")
    date_picker_button_xpath = "//button[span[contains(@class, 'MuiButton-startIcon')]]"
    
    try:
        # Use a short timeout to quickly check if we're already on the schedule page
        WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, date_picker_button_xpath)))
        print(" -> Initial state is already the 'Court Overview'. No extra click needed.")
    except TimeoutException:
        # If the date picker isn't found, we're likely on the initial screen.
        print(" -> Date picker not found. Assuming alternate view, now finding overview button...")
        # This flexible XPath handles both "Overzicht banen" and "Baanoverzicht"
        overview_button_xpath = "//button[contains(., 'Overzicht banen') or contains(., 'Baanoverzicht')]"
        overview_button = wait.until(EC.element_to_be_clickable((By.XPATH, overview_button_xpath)))
        print(f" -> Found overview button with text: '{overview_button.text}'. Clicking it...")
        overview_button.click()
        
        print(" -> Overview button clicked. Now waiting for the schedule view to load...")
        wait.until(EC.element_to_be_clickable((By.XPATH, date_picker_button_xpath)))
        print(" -> Schedule view (with date picker) is now active.")
    # --- END OF KEY FIX ---

    # --- REVISED AND MORE ROBUST DAY SELECTION PROCESS ---
    dialog_xpath = "//div[@role='dialog']"
    
    print(f" -> Opening date picker to select '{target_day}'...")
    wait.until(EC.element_to_be_clickable((By.XPATH, date_picker_button_xpath))).click()
    
    print(" -> VERIFICATION: Waiting for date picker dialog to be visible...")
    wait.until(EC.visibility_of_element_located((By.XPATH, dialog_xpath)))
    print(" -> CONFIRMED: Date picker dialog is open.")

    print(f" -> Clicking the '{target_day}' element in the picker...")
    # This XPath is more robust: it finds the text, then its clickable button ancestor.
    day_in_picker_xpath = f"//div[@role='dialog']//span[contains(text(), '{target_day}')]/ancestor::button[contains(@class, 'MuiPickersDay-root')]"
    wait.until(EC.element_to_be_clickable((By.XPATH, day_in_picker_xpath))).click()

    print(" -> VERIFICATION: Waiting for date picker dialog to close...")
    wait.until(EC.invisibility_of_element_located((By.XPATH, dialog_xpath)))
    print(" -> CONFIRMED: Date picker dialog has closed.")

    print(f" -> VERIFICATION: Waiting for main date button text to update to '{target_day}'...")
    wait.until(EC.text_to_be_present_in_element((By.XPATH, date_picker_button_xpath), target_day))
    print(f" -> CONFIRMED: Page has updated to show '{target_day}'.")
    
    print(" -> Waiting for any loading spinners to disappear after date change...")
    wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, "MuiBackdrop-root")))
    print(" -> Page is fully loaded and ready for scanning.")


def find_and_select_slot(driver, wait, start_time):
    """Scans the loaded schedule for an available slot and clicks it."""
    print("\nSTEP 3: FIND AND SELECT TIME SLOT")
    print(f" -> Scanning for the first available slot from {start_time} onwards...")
    
    hour = int(start_time.split(':')[0])
    end_time_str = f"{hour + 2:02d}:00"
    
    print(f" -> Search window is from {start_time} up to (but not including) {end_time_str}.")

    try:
        print(" -> Locating time labels in HTML (will scroll if needed)...")
        start_time_element = wait.until(EC.presence_of_element_located((By.XPATH, f"//span[text()='{start_time}']")))
        end_time_element = wait.until(EC.presence_of_element_located((By.XPATH, f"//span[text()='{end_time_str}']")))
        print(" -> Time labels found in HTML.")

        print(" -> Scrolling time labels into view to get accurate coordinates...")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", start_time_element)
        time.sleep(0.5)
        print(" -> Scroll complete.")

        start_y = start_time_element.location['y']
        end_y = end_time_element.location['y']
        tolerance = 5
        print(f" -> Search area defined by Y-coordinates: Start=~{start_y:.0f}px, End=~{end_y:.0f}px.")

        print(" -> Locating all court timeline containers...")
        court_slot_containers = wait.until(EC.visibility_of_all_elements_located((
            By.XPATH, "//div[div/span[contains(text(),'- Padel')]]/following-sibling::div"
        )))
        print(f" -> Found {len(court_slot_containers)} court timelines.")

        for index, container in enumerate(court_slot_containers[:7]):
            court_name = f"Padel Court {index + 1}"
            print(f" ---> Scanning {court_name}...")
            
            available_slots = container.find_elements(By.XPATH, ".//button[.//div[contains(@class, 'css-wpwytb')]]")
            
            if not available_slots:
                print(f"      - No available slots on this court.")
                continue

            for slot in available_slots:
                slot_y = slot.location['y']
                if (start_y - tolerance) <= slot_y < (end_y - tolerance):
                    print(f"      - ✅ SUCCESS! Found an available slot on {court_name} at Y-pos {slot_y:.0f}px.")
                    driver.execute_script("arguments[0].click();", slot)
                    return True

        print("\n -> SCAN COMPLETE: No available slots were found in the target time window on any court.")
        return False

    except TimeoutException as e:
        print(f" -> FATAL TIMEOUT in find_and_select_slot: Could not find a critical element on the page.")
        raise e


def complete_reservation(driver, wait):
    """Adds players and confirms the booking after a slot has been selected."""
    print("\nSTEP 4: COMPLETE RESERVATION")
    print(" -> Switching focus back to the main document...")
    driver.switch_to.default_content()

    print(" -> Waiting for reservation panel and selecting 60 minutes / 4 players...")
    duration_players_xpath = "//div[contains(@class, 'MuiBox-root')]//span[contains(text(), '60 min.')]/following-sibling::span[contains(text(), '4 Spelers')]"
    wait.until(EC.element_to_be_clickable((By.XPATH, duration_players_xpath))).click()

    print(" -> Opening player selection...")
    player_2_box = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'css-18nf95b') and .//span[text()='Speler 2']]")))
    player_2_box.click()
    time.sleep(1)

    players_to_add = ["Luc Brenkman", "Valentijn Wiegmans", "Willem Peters"]
    for player in players_to_add:
        print(f" -> Adding player: {player}...")
        add_button_xpath = f"//span[text()='{player}']/ancestor::div[contains(@class, 'css-1c1kq07')]/following-sibling::button"
        wait.until(EC.element_to_be_clickable((By.XPATH, add_button_xpath))).click()
        print(f" -> Successfully added {player}.")
        time.sleep(1)

    print(" -> Finalizing... attempting to confirm reservation.")
    confirm_button = wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Reservering bevestigen')]")))
    
    actions = ActionChains(driver)
    actions.move_to_element(confirm_button).click().perform()
    print(" -> Confirmation click sent.")

    print(" -> VERIFICATION: Waiting for success notification...")
    wait.until(EC.visibility_of_element_located((By.XPATH, "//*[contains(text(), 'succesvol')]")))
    print(" -> CONFIRMED: Success notification appeared.")


# --- Main Execution Block ---
if __name__ == "__main__":
    if not EMAIL or not PASSWORD:
        print("FATAL ERROR: EMAIL or PASSWORD environment variables not set in .env file.")
        sys.exit(1)

    driver, wait = get_driver_and_wait()
    
    try:
        login(driver, wait)
        navigate_and_select_day(driver, wait, TARGET_DAY)

        if find_and_select_slot(driver, wait, TARGET_START_TIME):
            complete_reservation(driver, wait)
            print("\n🎉 Reservation successfully completed!")
            driver.save_screenshot('success_screenshot.png')
            print(" -> Screenshot saved as success_screenshot.png")
        else:
            print("\nSCRIPT FINISHED: No available time slots found. Exiting.")
            driver.save_screenshot('no_slots_found.png')
            print(" -> Screenshot saved as no_slots_found.png")

    except Exception as e:
        print(f"\n❌ A FATAL AND UNEXPECTED ERROR OCCURRED: {type(e).__name__}")
        print(f"   Error details: {e}")
        print("   The script will now terminate.")
        
        # --- FILENAME FIX FOR GITHUB ARTIFACTS ---
        filename = "fatal_error.png"
        driver.save_screenshot(filename)
        print(f" -> A debug screenshot has been saved as: {filename}")
        sys.exit(1)
        
    finally:
        print("\nClosing browser session.")
        if 'driver' in locals() and driver:
            driver.quit()

