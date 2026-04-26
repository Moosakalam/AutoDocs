import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

def wake_app():
    url = "https://autodocs-cbwzxc3rbdu89rxb7ik8pt.streamlit.app/"
    chrome_options = Options()
    chrome_options.add_argument("--headless") # Runs without a window
    chrome_options.add_argument("--no-sandbox")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    time.sleep(10) # Wait for Streamlit to load the "Sleep" page

    try:
        # This clicks the literal "Wake up" button
        button = driver.find_element(By.XPATH, "//button[contains(text(), 'Yes, get this app back up')]")
        button.click()
        print("App was sleeping. Button clicked!")
        time.sleep(5)
    except:
        print("App was already awake or button not found.")
    
    driver.quit()

if __name__ == "__main__":
    wake_app()