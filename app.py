import streamlit as st
import re
import pdfplumber
import requests

st.set_page_config(page_title="FMCSA Email Extractor", layout="wide")

st.title("🚛 FMCSA PDF Email Extractor")
st.write("پی ڈی ایف اپ لوڈ کریں اور اسٹیٹس کے مطابق کیریئرز اور بروکرز کی ای میلز نکالیں۔")

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
                if "BROKER OF" in line.upper():
                    current_category = "Broker"
                elif "MOTOR CARRIER OF" in line.upper() or "FREIGHT FORWARDER" in line.upper():
                    current_category = "Carrier"
                
                # USDOT یا MC نمبر تلاش کرنا
                dot_match = re.search(r'(?:USDOT|MC|FF)\s*[-#]?\s*(\d+)', line, re.IGNORECASE)
                
                if dot_match:
                    num = dot_match.group(1)
                    extracted_records.append({
                        'type': current_category,
                        'id': num
                    })
    return extracted_records

def fetch_fmcsa_details(id_number):
    try:
        # FMCSA API Endpoint with Active WebKey
        url = f"https://mobile.fmcsa.dot.gov/qc/services/carriers/{id_number}?webKey=c323f46f4eb27eb294e75cb70d65427d1a5bf068"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            carrier = data.get('content', {}).get('carrier', {})
            
            if carrier:
                email = carrier.get('emailAddress')
                allowed = carrier.get('allowedToOperate', 'N')
                
                # اسٹیٹس چیک کریں
                if allowed == 'Y':
                    status = 'Active'
                elif allowed == 'N':
                    status = 'Inactive'
                elif 'P' in str(allowed):
                    status = 'Pending'
                else:
                    status = 'Rejected'
                    
                if email and "@" in email and email.lower() != "none":
                    return email.strip(), status
    except Exception:
        pass
    return None, None

uploaded_file = st.file_uploader("پی ڈی ایف فائل یہاں اپ لوڈ کریں", type=["pdf"])

if uploaded_file is not None:
    if st.button("Extract Emails"):
        with st.spinner("پی ڈی ایف سے ڈیٹا نکالا جا رہا ہے، براہ کرم انتظار کریں..."):
            records = extract_data_from_pdf(uploaded_file)
            
            results = {
                'Brokers': {'Active': [], 'Inactive': [], 'Pending': [], 'Rejected': []},
                'Carriers': {'Active': [], 'Inactive': [], 'Pending': [], 'Rejected': []}
            }
            
            progress_bar = st.progress(0)
            total = len(records)
            
            for index, record in enumerate(records):
                email, status = fetch_fmcsa_details(record['id'])
                category = 'Brokers' if record['type'] == 'Broker' else 'Carriers'
                
                if email and status:
                    results[category][status].append(email)
                
                if total > 0:
                    progress_bar.progress((index + 1) / total)
            
            # ڈوپلیکیٹ ای میلز ختم کرنا
            for cat in results:
                for st_key in results[cat]:
                    results[cat][st_key] = list(set(results[cat][st_key]))
            
            st.session_state['results'] = results
            st.success("پروسیسنگ مکمل ہو گئی ہے!")

if 'results' in st.session_state:
    results = st.session_state['results']
    
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
                        label="ای میل لسٹ:", 
                        value=email_str, 
                        height=250, 
                        key=f"{category_name}_{status}_text"
                    )
                    st.info("💡 ای میلز کاپی کرنے کے لیے اوپر والے باکس کے دائیں کونے میں دیے گئے Copy آئیکن پر کلک کریں۔")
                else:
                    st.warning("اس کیٹیگری میں کوئی ای میل نہیں ملی۔")

    with main_tab1:
        display_status_sections('Carriers')
        
    with main_tab2:
        display_status_sections('Brokers')
