import streamlit as st
from docx import Document
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import smtplib
import os
from datetime import datetime
import pytz

st.set_page_config(layout='wide')

def load_docx(file):
    try:
        doc = Document(file)
        return doc
    except Exception as e:
        st.error("Error loading document: {}".format(str(e)))
        return None

def get_doc_text(doc):
    return "\n".join([para.text for para in doc.paragraphs])

# Function to create a .txt file from the document text
def create_txt_file(doc_text, file_name):
    with open(file_name, 'w') as f:
        f.write(doc_text)
    return file_name

def get_timestamp():
    """Generate a formatted timestamp string in EST."""
    est = pytz.timezone('America/New_York')
    return datetime.now(est).strftime("%Y%m%d_%H%M%S")

def send_email(to_address, subject, body, attachment_path):
    from_address = 'eastridge.analytics@gmail.com'
    password = 'haua virs tljt wrya'  # Use the app-specific password generated from Google

    # Add timestamp to the subject
    timestamped_subject = f"{subject} - {get_timestamp()}"

    # Set up the MIME
    message = MIMEMultipart()
    message['From'] = from_address
    message['To'] = to_address
    message['Subject'] = timestamped_subject

    # Add body and attachment
    message.attach(MIMEText(body, 'plain'))
    if attachment_path:
        part = MIMEBase('application', 'octet-stream')
        with open(attachment_path, 'rb') as attachment:
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(attachment_path)}")
        message.attach(part)

    # Create SMTP session
    session = smtplib.SMTP('smtp.gmail.com', 587)
    session.starttls()
    session.login(from_address, password)
    text = message.as_string()
    session.sendmail(from_address, to_address, text)
    session.quit()

    return "Email sent successfully! Please allow 48 hours for Eastridge Analytics to reply."


st.markdown("<h1 style='text-align: center;'>Patentability and Commercialization Assessment</h1>", unsafe_allow_html=True)

# Upload docx file
uploaded_file = st.file_uploader("Drop a .docx file of the Invention Disclosure Form here", type="docx")

if uploaded_file:
    doc = load_docx(uploaded_file)
    
    if doc:
        doc_text = get_doc_text(doc)
        
        st.subheader("Document Content")
        # st.text_area("Document Text", doc_text, height=200)
        
        # Add some vertical space
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Center-align the button using columns
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            if st.button("Send Email for Assessment", key="send_email", use_container_width=True):
                # Create a .txt file from the document text
                txt_file_name = "document_content.txt"
                txt_file_path = create_txt_file(doc_text, txt_file_name)
                
                result = send_email("info@eastridge-analytics.com", "Document for Assessment", "Please find attached the document content in .txt format for assessment.", txt_file_path)
                st.success(result)
                
                # Clean up the generated .txt file after sending
                if os.path.exists(txt_file_path):
                    os.remove(txt_file_path)
        
        # Add some vertical space
        st.markdown("<br>", unsafe_allow_html=True)
        

else:
    st.warning("Please upload a .docx file.")
