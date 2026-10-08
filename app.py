import streamlit as st
import re
import pdfplumber
import requests

# App Configuration
st.set_page_config(page_title="FMCSA Email Extractor", layout="wide")

st.title("🚛 FMCSA PDF Email Extractor")
st.write("پی ڈی ایف اپ لوڈ کریں اور سٹیٹس کے مطابق کیریئرز اور بروکرز کی ای میلز نکالیں۔")

def extract_data_from_pdf(pdf_file):
    extracted_records = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            lines = text.split('\n')
            current_category = "Carrier"
            for line in lines:
                if "Broker of" in line:
                    current_category = "Broker"
                elif "Motor Carrier of" in line or "Freight Forwarder" in line:
                    current_category = "Carrier"
                
                dot_match = re.search(r'USDOT\s*#?\s*(\d+)', line, re.IGNORECASE)
                mc_match = re.search(r'MC-\d+', line, re.IGNORECASE)
                
                if dot_match:
                    dot_num = dot_match.group(1)
                    extracted_records.append({
                        'type': current_category,
                        'dot': dot_num,
                        'mc': mc_match.group(0) if mc_match else None
                    })
    return extracted_records

def fetch_fmcsa_details(dot_number):
    try:
        url = f"https://mobile.fmcsa.dot.gov/qc/services/carriers/{dot_number}?webKey=YOUR_API_KEY"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            carrier = data.get('content', {}).get('carrier', {})
            email = carrier.get('emailAddress', None)
            statusCode = carrier.get('allowedToOperate', 'Inactive') 
            
            if statusCode == 'Y':
                status = 'Active'
            elif statusCode == 'N':
                status = 'Inactive'
            elif 'Pending' in statusCode:
                status = 'Pending'
            else:
                status = 'Rejected'
            return email, status
    except Exception:
        pass
    return None, "Inactive"

# File Uploader
uploaded_file = st.file_uploader("پی ڈی ایف فائل یہاں اپ لوڈ کریں", type=["pdf"])

if uploaded_file is not None:
    if st.button("Extract Emails"):
        with st.spinner("پی ڈی ایف پروسیس ہو رہی ہے، براہ کرم انتظار کریں..."):
            records = extract_data_from_pdf(uploaded_file)
            
            results = {
                'Brokers': {'Active': [], 'Inactive': [], 'Pending': [], 'Rejected': []},
                'Carriers': {'Active': [], 'Inactive': [], 'Pending': [], 'Rejected': []}
            }
            
            for record in records:
                email, status = fetch_fmcsa_details(record['dot'])
                category = 'Brokers' if record['type'] == 'Broker' else 'Carriers'
                
                if email and email != 'No Email Found':
                    results[category][status].append(email)
            
            # Remove Duplicates
            for cat in results:
                for st_key in results[cat]:
                    results[cat][st_key] = list(set(results[cat][st_key]))
            
            st.session_state['results'] = results
            st.success("پروسیسنگ مکمل ہو گئی ہے!")

# Display Results
if 'results' in st.session_state:
    results = st.session_state['results']
    
    # Category Tabs
    main_tab1, main_tab2 = st.tabs(["🚛 Carriers Emails", "🏢 Brokers Emails"])
    
    def display_status_sections(category_name):
        status_tabs = st.tabs(["Active", "Inactive", "Pending", "Rejected"])
        statuses = ["Active", "Inactive", "Pending", "Rejected"]
        
        for i, status in enumerate(statuses):
            with status_tabs[i]:
                emails = results[category_name][status]
                st.subheader(f"{status} {category_name} ({len(emails)})")
                
                if emails:
                    email_str = "\n".join(emails)
                    st.text_area(
                        label=f"{status} ای میلز کی لسٹ:", 
                        value=email_str, 
                        height=200, 
                        key=f"{category_name}_{status}_text"
                    )
                    st.info("💡 تمام ای میلز کاپی کرنے کے لیے اوپر دیے گئے باکس کے اوپر کونے میں 'Copy' ائیکن پر کلک کریں یا آل سلیکٹ کریں۔")
                else:
                    st.warning("کوئی ای میل نہیں ملی۔")

    with main_tab1:
        display_status_sections('Carriers')
        
    with main_tab2:
        display_status_sections('Brokers')
