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
# === Chrome Driver Setup (Local Execution) ===
# ==================================================================
@st.cache_resource
def setup_driver():
    """Setup Chrome WebDriver for local execution"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")  # New headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

# ==================================================================
# === Helper Functions for Stale Elements ===
# ==================================================================
def get_stale_proof_text(driver, locator, max_attempts=5):
    """Get element text, retrying if stale."""
    attempts = 0
    while attempts < max_attempts:
        try:
            element = WebDriverWait(driver, 10).until(EC.presence_of_element_located(locator))
            return element.text
        except StaleElementReferenceException:
            attempts += 1
            st.warning(f"Element stale, retrying {attempts}/{max_attempts}...")
            time.sleep(1)
    raise Exception(f"Could not get text from {locator}")

def stale_proof_click(driver, locator, max_attempts=5):
    """Click element, retrying if stale."""
    attempts = 0
    while attempts < max_attempts:
        try:
            element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(locator))
            driver.execute_script("arguments[0].click();", element)
            return True
        except (StaleElementReferenceException, TimeoutException):
            attempts += 1
            st.warning(f"Click failed, retrying {attempts}/{max_attempts}...")
            time.sleep(1)
    raise Exception(f"Could not click element at {locator}")

# ==================================================================
# === Main Automation Function ===
# ==================================================================
def perform_automation(username, password, assessment_data):
    try:
        st.info("🚀 Launching browser...")
        driver = setup_driver()
        wait = WebDriverWait(driver, 20)
    except Exception as e:
        st.error(f"Chrome launch failed: {e}")
        return

    # Login
    try:
        st.info("Opening login page...")
        driver.get("https://nxtwave-assessments-backend-topin-prod-apis.ccbp.in/admin/")
        wait.until(EC.presence_of_element_located((By.ID, "id_username"))).send_keys(username)
        driver.find_element(By.ID, "id_password").send_keys(password)
        driver.find_element(By.CSS_SELECTOR, 'input[type="submit"]').click()
        wait.until(EC.presence_of_element_located((By.ID, "user-tools")))
        st.success("✅ Login successful.")
    except Exception as e:
        st.error(f"Login failed: {e}")
        driver.quit()
        return

    lines = [line.strip() for line in assessment_data.strip().split("\n") if line.strip()]
    total = len(lines)
    if total == 0:
        st.warning("No data to process.")
        driver.quit()
        return

    progress = st.progress(0)
    results = []

    for i, line in enumerate(lines):
        result = {"ID": "", "Status": "Failed", "Details": ""}
        try:
            parts = line.split(",")
            if len(parts) != 2:
                result["Details"] = "Malformed line"
                results.append(result)
                progress.progress((i + 1) / total)
                continue

            assess_id, date_str = parts[0].strip(), parts[1].strip()
            result["ID"] = assess_id

            try:
                completion_dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                completion_dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M")

            # Example: Go to config page
            driver.get("https://nxtwave-assessments-backend-topin-prod-apis.ccbp.in/admin/nw_assessments_core/orgassessreviewconfig/add/")
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            st.write(f"Processing {assess_id}... (date {completion_dt})")

            # TODO: Insert your full automation steps here (click, fill form, etc.)
            result["Status"] = "Success"
            result["Details"] = "Processed successfully"

        except Exception as e:
            result["Details"] = f"Error: {e}"
        finally:
            results.append(result)
            progress.progress((i + 1) / total)

    driver.quit()
    st.subheader("📊 Summary")
    st.dataframe(pd.DataFrame(results))

# ==================================================================
# === Streamlit UI ===
# ==================================================================
def main():
    st.set_page_config(page_title="Assessment Automation", layout="wide")
    st.title("🚀 Assessment Review Automation")

    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
    with col2:
        st.write("Format: AssessmentID, YYYY-MM-DD HH:MM:SS")
        example = "bf637137-1915-47fa-81c0-6b0a14916220, 2023-10-27 15:30:00"
        assessment_data_input = st.text_area("Assessment data", placeholder=example, height=200)

    if st.button("▶️ Start Automation", type="primary"):
        if not username or not password:
            st.error("Username and password required.")
        elif not assessment_data_input.strip():
            st.error("Please provide assessment data.")
        else:
            perform_automation(username, password, assessment_data_input)

if __name__ == "__main__":
    main()
