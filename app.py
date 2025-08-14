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
    """Setup Chrome WebDriver for Windows automatically using webdriver_manager"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")  # New headless mode
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")

    # Automatically download correct ChromeDriver version
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

            # Parse datetime
            try:
                completion_dt = datetime.strptime(completion_time_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                completion_dt = datetime.strptime(completion_time_str, '%Y-%m-%d %H:%M')

            # --- Step 1: Create Review Config ---
            add_config_url = "https://nxtwave-assessments-backend-topin-prod-apis.ccbp.in/admin/nw_assessments_core/orgassessreviewconfig/add/"
            current_dt = datetime.now()
            time_delta_seconds = max(int((current_dt - completion_dt).total_seconds()), 0)

            driver.get(add_config_url)
            wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "span[aria-labelledby='select2-id_org_assess-container']"))).click()
            search_box = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "select2-search__field")))
            search_box.send_keys(original_assess_id[:8])

            suggestion_locator = (By.XPATH, f"//li[contains(@class, 'select2-results__option') and contains(text(), '{original_assess_id}')]")
            wait.until(EC.element_to_be_clickable(suggestion_locator)).click()

            wait.until(EC.presence_of_element_located((By.ID, "id_review_mode"))).send_keys('ASSESS_COMPLETION')
            time_input = driver.find_element(By.ID, "id_time_to_enable_review_in_secs")
            time_input.clear()
            time_input.send_keys(str(time_delta_seconds))
            driver.find_element(By.NAME, "_save").click()
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.success")))
            st.success(f"✅ Step 1 complete for {original_assess_id}")
            result["Status"] = "Success"
            result["Details"] += "Review config created; "

            # --- Step 2: Find New Assessment ID ---
            org_assess_url = "https://nxtwave-assessments-backend-topin-prod-apis.ccbp.in/admin/nw_assessments_core/organisationassessment/"
            driver.get(org_assess_url)
            search_bar = wait.until(EC.presence_of_element_located((By.ID, "searchbar")))
            search_bar.clear()
            search_bar.send_keys(original_assess_id[:8])
            driver.find_element(By.CSS_SELECTOR, 'input[value="Search"]').click()

            new_assess_id_locator = (By.CSS_SELECTOR, "#result_list td.field-assessment_id")
            new_assessment_id = get_stale_proof_text(driver, new_assess_id_locator)
            st.success(f"✅ Found new assessment ID: {new_assessment_id}")
            result["Details"] += f"New ID: {new_assessment_id}; "

            # --- Step 3: Find Unit IDs ---
            assess_level_url = "https://nxtwave-assessments-backend-topin-prod-apis.ccbp.in/admin/nw_assessments_core/assessmentlevel/"
            driver.get(assess_level_url)
            search_bar = wait.until(EC.presence_of_element_located((By.ID, "searchbar")))
            search_bar.clear()
            search_bar.send_keys(new_assessment_id[:8])
            driver.find_element(By.CSS_SELECTOR, 'input[value="Search"]').click()

            unit_ids = []
            attempts = 0
            while attempts < 3:
                try:
                    unit_id_elements = wait.until(EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "#result_list td.field-unit_id")))
                    unit_ids = [elem.text for elem in unit_id_elements]
                    break
                except StaleElementReferenceException:
                    attempts += 1
                    st.warning(f"Retrying to read Unit IDs (Attempt {attempts}/3)...")
                    time.sleep(1)

            if not unit_ids:
                st.error("Could not find any Unit IDs.")
                result["Details"] += "No Unit IDs found; "
                results.append(result)
                progress_bar.progress((i + 1) / total_lines)
                continue

            st.success(f"✅ Found {len(unit_ids)} Unit ID(s): {unit_ids}")
            result["Details"] += f"Found {len(unit_ids)} units; "

            # --- Step 4: Enable Review for Each Unit ---
            exam_url = "https://nxtwave-assessments-backend-topin-prod-apis.ccbp.in/admin/nkb_exam/exam/"
            for unit_id in unit_ids:
                driver.get(exam_url)
                search_bar = wait.until(EC.presence_of_element_located((By.ID, "searchbar")))
                search_bar.clear()
                search_bar.send_keys(unit_id[:8])
                driver.find_element(By.CSS_SELECTOR, 'input[value="Search"]').click()

                exam_link_locator = (By.CSS_SELECTOR, "#result_list th.field-id a")
                stale_proof_click(driver, exam_link_locator)

                review_checkbox = wait.until(EC.presence_of_element_located((By.ID, "id_enable_attempt_review")))
                if not review_checkbox.is_selected():
                    review_checkbox.click()
                driver.find_element(By.NAME, "_save").click()
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.success")))
                result["Details"] += f"Enabled review for {unit_id}; "

        except Exception as e:
            st.error(f"❌ Failed while processing ID: {original_assess_id}")
            st.exception(e)
            result["Status"] = "Failed"
            result["Details"] += str(e)
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
    st.title("🚀 ChromeDriver-Fixed Assessment Automation (Windows Ready)")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.header("Admin Credentials")
        username = st.text_input("Django Admin Username")
        password = st.text_input("Django Admin Password", type="password")
    with col2:
        st.header("Assessment Data")
        example_data = """bf637137-1915-47fa-81c0-6b0a14916220, 2023-10-27 15:30:00
9f3c4f8e-c2d2-4f44-b87e-f42950a02a3c, 2025-02-28 13:00:00"""
        assessment_data_input = st.text_area(
            "Paste assessment data below (ID, YYYY-MM-DD HH:MM:SS):",
            height=250,
            placeholder=example_data
        )

    if st.button("▶️ Start Automation"):
        if not all([username, password, assessment_data_input]):
            st.error("Please fill all fields")
        else:
            with st.spinner("Processing assessments..."):
                perform_automation(username, password, assessment_data_input)

if __name__ == "__main__":
    main()
