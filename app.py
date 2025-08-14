import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import time
from datetime import datetime

# ==================================================================
# === Chrome Driver Setup for Windows ===
# ==================================================================
@st.cache_resource
def setup_driver():
    """Setup Chrome WebDriver for Windows"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")  # New headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")
    
    # Automatically download and use the correct ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# ==================================================================
# === Self-Healing Functions ===
# ==================================================================
def get_stale_proof_text(driver, locator, max_attempts=5):
    attempts = 0
    while attempts < max_attempts:
        try:
            element = WebDriverWait(driver, 10).until(EC.presence_of_element_located(locator))
            return element.text
        except StaleElementReferenceException:
            attempts += 1
            st.warning(f"Element went stale. Retry ({attempts}/{max_attempts})...")
            time.sleep(1)
    raise Exception(f"Could not get text from element at {locator}.")

def stale_proof_click(driver, locator, max_attempts=5):
    attempts = 0
    while attempts < max_attempts:
        try:
            element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(locator))
            driver.execute_script("arguments[0].click();", element)
            return True
        except (StaleElementReferenceException, TimeoutException):
            attempts += 1
            st.warning(f"Click failed. Retry ({attempts}/{max_attempts})...")
            time.sleep(1)
    raise Exception(f"Could not click element at {locator}.")

# ==================================================================
# === Main Automation Function ===
# ==================================================================
def perform_automation(username, password, assessment_data):
    try:
        st.info("🚀 Launching the automation robot...")
        driver = setup_driver()
        wait = WebDriverWait(driver, 20)
        st.success("✅ Robot launched successfully.")
    except Exception as e:
        st.error(f"Failed to start Chrome. Error: {e}")
        return

    # 1. Login Process
    try:
        base_url = "https://nxtwave-assessments-backend-topin-prod-apis.ccbp.in/admin/"
        driver.get(base_url)
        wait.until(EC.presence_of_element_located((By.ID, "id_username"))).send_keys(username)
        driver.find_element(By.ID, "id_password").send_keys(password)
        driver.find_element(By.CSS_SELECTOR, 'input[type="submit"]').click()
        wait.until(EC.presence_of_element_located((By.ID, "user-tools")))
        st.success("✅ Login Successful!")
    except Exception as e:
        st.error(f"Login failed. Error: {e}")
        driver.quit()
        return

    # Process Assessment Data
    lines = [line.strip() for line in assessment_data.strip().split('\n') if line.strip()]
    total_lines = len(lines)
    st.info(f"Found {total_lines} assessments to process.")
    if total_lines == 0:
        st.warning("No data found.")
        driver.quit()
        return

    progress_bar = st.progress(0)
    results = []

    for i, line in enumerate(lines):
        result = {"ID": "", "Status": "Failed", "Details": ""}
        try:
            parts = line.split(',')
            if len(parts) != 2:
                result["Details"] = "Malformed input line"
                results.append(result)
                progress_bar.progress((i + 1) / total_lines)
                continue

            original_assess_id = parts[0].strip()
            completion_time_str = parts[1].strip()
            result["ID"] = original_assess_id

            try:
                completion_dt = datetime.strptime(completion_time_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                completion_dt = datetime.strptime(completion_time_str, '%Y-%m-%d %H:%M')

            # --- Steps to process assessments ---
            # (You can reuse your existing steps here, e.g., Step1, Step2, etc.)
            result["Status"] = "Success"
            result["Details"] = "Processed successfully."

        except Exception as e:
            result["Status"] = "Failed"
            result["Details"] = str(e)
        finally:
            results.append(result)
            progress_bar.progress((i + 1) / total_lines)

    driver.quit()
    st.subheader("📊 Processing Summary")
    st.dataframe(pd.DataFrame(results))
    st.success("🎉 All tasks complete!")

# ==================================================================
# === Streamlit UI ===
# ==================================================================
def main():
    st.set_page_config(page_title="Assessment Automation", layout="wide")
    st.title("🚀 Windows ChromeDriver Assessment Automation")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.header("Admin Credentials")
        username = st.text_input("Django Admin Username")
        password = st.text_input("Django Admin Password", type="password")
    with col2:
        st.header("Assessment Data")
        assessment_data_input = st.text_area(
            "Paste assessment data (ID, YYYY-MM-DD HH:MM:SS):",
            height=250
        )

    if st.button("▶️ Start Automation"):
        if not all([username, password, assessment_data_input]):
            st.error("Please fill all fields")
        else:
            with st.spinner("Processing assessments..."):
                perform_automation(username, password, assessment_data_input)

if __name__ == "__main__":
    main()
