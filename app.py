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
import os

# ==================================================================
# === Optimized Chrome Driver Setup for Streamlit Cloud ===
# ==================================================================
@st.cache_resource
def setup_driver():
    """Setup Chrome WebDriver with Streamlit Cloud compatibility"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")
    options.add_argument("--remote-debugging-port=9222")
    
    # Streamlit Cloud specific configuration
    options.binary_location = "/usr/bin/google-chrome"
    
    # Install ChromeDriver
    service = Service(ChromeDriverManager().install())
    
    return webdriver.Chrome(service=service, options=options)

# ==================================================================
# === The "Nuke-Proof" Self-Healing Functions ===
# ==================================================================
def get_stale_proof_text(driver, locator, max_attempts=5):
    """Robust way to get text from an element that might go stale."""
    attempts = 0
    while attempts < max_attempts:
        try:
            element = WebDriverWait(driver, 10).until(EC.presence_of_element_located(locator))
            return element.text
        except StaleElementReferenceException:
            attempts += 1
            st.warning(f"Element became stale while reading text. Retrying ({attempts}/{max_attempts})...")
            time.sleep(1)
    raise Exception(f"Could not get text from element at {locator} after {max_attempts} attempts.")

def stale_proof_click(driver, locator, max_attempts=5):
    """Robust way to click an element that might go stale."""
    attempts = 0
    while attempts < max_attempts:
        try:
            element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable(locator))
            driver.execute_script("arguments[0].click();", element)
            return True
        except (StaleElementReferenceException, TimeoutException):
            attempts += 1
            st.warning(f"Click failed, element might be stale. Retrying ({attempts}/{max_attempts})...")
            time.sleep(1)
    raise Exception(f"Could not click the element at {locator} after {max_attempts} attempts.")

# ==================================================================
# === Main Automation Function ===
# ==================================================================
def perform_automation(username, password, assessment_data):
    """Main automation function to process assessments."""
    # Setup Selenium WebDriver
    try:
        st.info("🚀 Launching the automation robot...")
        driver = setup_driver()
        wait = WebDriverWait(driver, 20)
        st.success("✅ Robot launched successfully.")
    except Exception as e:
        st.error(f"Failed to start Chrome. Please ensure Chrome is installed. Error: {e}")
        return

    # 1. Login Process
    try:
        st.info("Navigating to the login page...")
        base_url = "https://nxtwave-assessments-backend-topin-prod-apis.ccbp.in/admin/"
        driver.get(base_url)
        st.info("Entering credentials...")
        wait.until(EC.presence_of_element_located((By.ID, "id_username"))).send_keys(username)
        driver.find_element(By.ID, "id_password").send_keys(password)
        st.info("Clicking 'Log In' button...")
        driver.find_element(By.CSS_SELECTOR, 'input[type="submit"]').click()
        wait.until(EC.presence_of_element_located((By.ID, "user-tools")))
        st.success("✅ Login Successful! Preparing to process data.")
    except Exception as e:
        st.error(f"Login failed. Please double-check credentials. Error: {e}")
        driver.quit()
        return

    # Process each Assessment ID
    lines = [line.strip() for line in assessment_data.strip().split('\n') if line.strip()]
    total_lines = len(lines)
    
    st.info(f"Found {total_lines} assessments to process.")
    if total_lines == 0:
        st.warning("No data found to process.")
        driver.quit()
        return
        
    progress_bar = st.progress(0)
    results = []
    
    # Main loop for each assessment
    for i, line in enumerate(lines):
        st.markdown(f"<hr>", unsafe_allow_html=True)
        result = {"ID": "", "Status": "Failed", "Details": ""}
        try:
            # Parse the input line
            parts = line.split(',')
            if len(parts) != 2:
                st.warning(f"Skipping malformed line ({i+1}): '{line}'. Please use 'ID, YYYY-MM-DD HH:MM:SS' format.")
                result["Details"] = "Malformed input line"
                results.append(result)
                progress_bar.progress((i + 1) / total_lines)
                continue
            
            original_assess_id = parts[0].strip()
            completion_time_str = parts[1].strip()
            result["ID"] = original_assess_id
            
            st.write(f"▶️ **Processing ({i+1}/{total_lines}): {original_assess_id}**")

            # STEP 1: Create Review Config
            st.subheader("Step 1: Creating Review Config")
            try:
                completion_dt = datetime.strptime(completion_time_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    completion_dt = datetime.strptime(completion_time_str, '%Y-%m-%d %H:%M')
                except ValueError:
                    st.error(f"Invalid datetime format for {original_assess_id}. Use 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD HH:MM'")
                    result["Details"] = "Invalid datetime format"
                    results.append(result)
                    progress_bar.progress((i + 1) / total_lines)
                    continue
            
            add_config_url = "https://nxtwave-assessments-backend-topin-prod-apis.ccbp.in/admin/nw_assessments_core/orgassessreviewconfig/add/"
            current_dt = datetime.now()
            time_delta_seconds = int((current_dt - completion_dt).total_seconds())
            if time_delta_seconds < 0:
                time_delta_seconds = 0
            
            driver.get(add_config_url)
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "span[aria-labelledby='select2-id_org_assess-container']"))).click()
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
            st.success("✅ Step 1 complete.")
            result["Status"] = "Success"
            result["Details"] += "Review config created; "

            # STEP 2: Find New Assessment ID
            st.subheader("Step 2: Finding New Assessment ID")
            org_assess_url = "https://nxtwave-assessments-backend-topin-prod-apis.ccbp.in/admin/nw_assessments_core/organisationassessment/"
            driver.get(org_assess_url)
            search_bar = wait.until(EC.presence_of_element_located((By.ID, "searchbar")))
            search_bar.clear()
            search_bar.send_keys(original_assess_id[:8])
            driver.find_element(By.CSS_SELECTOR, 'input[value="Search"]').click()
            
            st.info("Finding 'ASSESSMENT ID' from results...")
            new_assess_id_locator = (By.CSS_SELECTOR, "#result_list td.field-assessment_id")
            new_assessment_id = get_stale_proof_text(driver, new_assess_id_locator)
            st.success(f"✅ Found new assessment ID: **{new_assessment_id}**")
            result["Details"] += f"New ID: {new_assessment_id}; "

            # STEP 3: Find Unit ID(s)
            st.subheader("Step 3: Finding Unit ID(s)")
            assess_level_url = "https://nxtwave-assessments-backend-topin-prod-apis.ccbp.in/admin/nw_assessments_core/assessmentlevel/"
            driver.get(assess_level_url)
            
            search_term = new_assessment_id[:8]
            st.info(f"Searching on Assessment levels page with term: '{search_term}'")
            search_bar = wait.until(EC.presence_of_element_located((By.ID, "searchbar")))
            search_bar.clear()
            search_bar.send_keys(search_term)
            driver.find_element(By.CSS_SELECTOR, 'input[value="Search"]').click()
            
            st.info("Finding all Unit IDs from results...")
            unit_ids = []
            attempts = 0
            while attempts < 3:
                try:
                    unit_id_elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#result_list td.field-unit_id")))
                    unit_ids = [elem.text for elem in unit_id_elements]
                    break
                except StaleElementReferenceException:
                    attempts += 1
                    st.warning(f"Page refreshed. Retrying to read Unit IDs (Attempt {attempts}/3)...")
                    time.sleep(1)
            
            if not unit_ids:
                st.error("Could not find any Unit IDs.")
                result["Details"] += "No Unit IDs found; "
                results.append(result)
                progress_bar.progress((i + 1) / total_lines)
                continue
                
            st.success(f"✅ Found {len(unit_ids)} Unit ID(s) to process: {unit_ids}")
            result["Details"] += f"Found {len(unit_ids)} units; "

            # STEP 4: Enable Review for EACH Unit ID
            st.subheader("Step 4: Enabling Attempt Review on Final Exam(s)")
            exam_url = "https://nxtwave-assessments-backend-topin-prod-apis.ccbp.in/admin/nkb_exam/exam/"

            for unit_id in unit_ids:
                st.write(f"--- Processing Unit ID: **{unit_id}** ---")
                driver.get(exam_url)
                
                search_term = unit_id[:8]
                st.info(f"Searching on Exam page with term: '{search_term}'")
                search_bar = wait.until(EC.presence_of_element_located((By.ID, "searchbar")))
                search_bar.clear()
                search_bar.send_keys(search_term)
                driver.find_element(By.CSS_SELECTOR, 'input[value="Search"]').click()
                
                st.info("Clicking on the final Exam link...")
                exam_link_locator = (By.CSS_SELECTOR, "#result_list th.field-id a")
                stale_proof_click(driver, exam_link_locator)

                st.info("Checking 'Enable attempt review' checkbox...")
                review_checkbox = wait.until(EC.presence_of_element_located((By.ID, "id_enable_attempt_review")))
                if not review_checkbox.is_selected():
                    review_checkbox.click()
                    st.write("Checkbox was off. It has been ENABLED.")
                else:
                    st.write("Checkbox was already ON.")
                
                st.info("Saving final changes...")
                driver.find_element(By.NAME, "_save").click()
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "li.success")))
                st.success(f"✅ Final save complete for Unit ID: {unit_id}")
                result["Details"] += f"Enabled review for {unit_id}; "
            
        except Exception as e:
            st.error(f"❌ Failed while processing ID: **{original_assess_id}**. See error below.")
            st.exception(e)
            result["Status"] = "Failed"
            result["Details"] += f"Error: {str(e)}"
        finally:
            results.append(result)
            progress_bar.progress((i + 1) / total_lines)

    driver.quit()
    
    # Display results summary
    st.subheader("📊 Processing Summary")
    results_df = pd.DataFrame(results)
    st.dataframe(results_df)
    
    st.success("🎉🎉🎉 All tasks complete! The robot has finished its work.")
    st.balloons()

# ==================================================================
# === Streamlit UI ===
# ==================================================================
def main():
    st.set_page_config(
        page_title="Assessment Automation",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🚀 Full Assessment Workflow Automation Tool")
    st.markdown("""
        This tool performs the complete, multi-step process for enabling assessment reviews.
        **Important:** Processing may take several minutes depending on the number of assessments.
    """)
    
    with st.expander("🔒 Security Notice"):
        st.warning("""
            - Never share your admin credentials
            - This session is not persistent - credentials are not stored
            - For security, close the browser after completing your tasks
        """)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.header("1. Admin Credentials")
        username = st.text_input("Django Admin Username")
        password = st.text_input("Django Admin Password", type="password")
        
    with col2:
        st.header("2. Assessment Data")
        st.markdown("""
            **Required Format:**  
            `AssessmentID, CompletionDateTime`  
            One entry per line
        """)
        
        example_data = """bf637137-1915-47fa-81c0-6b0a14916220, 2023-10-27 15:30:00
9f3c4f8e-c2d2-4f44-b87e-f42950a02a3c, 2025-02-28 13:00:00"""
        
        assessment_data_input = st.text_area(
            "Paste assessment data below:",
            height=250,
            placeholder=example_data
        )
    
    st.divider()
    
    if st.button("▶️ Start Automation", type="primary", use_container_width=True):
        if not username or not password:
            st.error("Please enter both username and password")
        elif not assessment_data_input or len(assessment_data_input.strip()) == 0:
            st.error("Please paste assessment data to process")
        else:
            with st.spinner("🚦 Automation in progress - please don't close this tab..."):
                perform_automation(username, password, assessment_data_input)

if __name__ == "__main__":
    main()