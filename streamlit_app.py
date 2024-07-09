import streamlit as st
import openai
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from docx import Document
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import smtplib
import os
from datetime import datetime
import pytz

import streamlit as st

try:
    from langchain.chat_models import ChatOpenAI
    st.success("langchain_community module is successfully imported!")
except ImportError as e:
    st.error(f"Error importing langchain_community module: {e}")


st.set_page_config(layout='wide')

# Use secrets for sensitive information
openai_api_key = st.secrets["openai"]["api_key"]
email_address = st.secrets["email"]["address"]
email_password = st.secrets["email"]["password"]

if not openai_api_key:
    st.error("OpenAI API key is not set in the secrets file.")
    st.stop()

def load_docx(file):
    try:
        doc = Document(file)
        return doc
    except Exception as e:
        st.error(f"Error loading document: {str(e)}")
        return None

def get_doc_text(doc):
    return "\n".join([para.text for para in doc.paragraphs])

def create_txt_file(doc_text, file_name):
    try:
        with open(file_name, 'w') as f:
            f.write(doc_text)
        return file_name
    except IOError as e:
        st.error(f"Error creating text file: {str(e)}")
        return None

def get_timestamp():
    est = pytz.timezone('America/New_York')
    return datetime.now(est).strftime("%Y%m%d_%H%M%S")

def generate_responses(doc_text):
    try:
        chat_llm = ChatOpenAI(temperature=0.8, openai_api_key=openai_api_key, model="gpt-4o")

        prompts = {
            "summary": "Provide a summary of the above information in 50-200 words. Ensure the summary is formatted as a paragraph.",
            "potential_customers": "Based on the above information, list potential customers for this idea in bullet points. Ensure each bullet point starts with a hyphen and a space.",
            "market_report": "Generate a market report based on the above information between 100-500 words. Ensure the report is formatted as paragraphs.",
            "similar_products": "List similar products related to this idea in bullet points. Ensure each bullet point starts with a hyphen and a space.",
            "provisional_patent": "Draft a provisional patent based on the above information. Format it as Patent_Title | Patent_Abstract | Patent_Claims and ensure each section is clearly labeled."
        }

        responses = {}
        for key, prompt_text in prompts.items():
            prompt_template = PromptTemplate(template="{doc_text}\n\n{prompt_text}", input_variables=["doc_text", "prompt_text"])
            chat_chain = LLMChain(llm=chat_llm, prompt=prompt_template)
            input_data = {"doc_text": doc_text, "prompt_text": prompt_text}
            response = chat_chain.generate([input_data])
            responses[key] = response.generations[0][0].text if response.generations else "No response generated"

        return responses
    except Exception as e:
        st.error(f"Error generating responses: {str(e)}")
        return None

def process_docx(uploaded_file):
    doc = load_docx(uploaded_file)
    if doc:
        return get_doc_text(doc)
    return None

def display_responses(responses):
    if responses:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Summary")
            st.markdown(f"<div style='border:1px solid black;padding:10px;'>{responses['summary']}</div>", unsafe_allow_html=True)
            
        with col2:
            st.subheader("Potential Customers")
            st.markdown(f"<div style='border:1px solid black;padding:10px;'>{responses['potential_customers']}</div>", unsafe_allow_html=True)

        col3, col4 = st.columns(2)
        with col3:
            st.subheader("Market Report")
            st.markdown(f"<div style='border:1px solid black;padding:10px;'>{responses['market_report']}</div>", unsafe_allow_html=True)
            
        with col4:
            st.subheader("Similar Products")
            st.markdown(f"<div style='border:1px solid black;padding:10px;'>{responses['similar_products']}</div>", unsafe_allow_html=True)

        st.subheader("Provisional Patent Draft")
        st.markdown(f"<div style='border:1px solid black;padding:10px;'>{responses['provisional_patent']}</div>", unsafe_allow_html=True)
    else:
        st.error("No responses to display.")

def send_email(to_address, subject, body, attachment_path):
    try:
        from_address = email_address
        password = email_password

        timestamped_subject = f"{subject} - {get_timestamp()}"

        message = MIMEMultipart()
        message['From'] = from_address
        message['To'] = to_address
        message['Subject'] = timestamped_subject

        message.attach(MIMEText(body, 'plain'))
        if attachment_path:
            with open(attachment_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(attachment_path)}")
            message.attach(part)

        with smtplib.SMTP('smtp.gmail.com', 587) as session:
            session.starttls()
            session.login(from_address, password)
            text = message.as_string()
            session.sendmail(from_address, to_address, text)

        return "Email sent successfully! Please allow 48 hours for Eastridge Analytics to reply."
    except Exception as e:
        st.error(f"Error sending email: {str(e)}")
        return None

# Initialize session state
if "button_clicked" not in st.session_state:
    st.session_state.button_clicked = False

st.markdown("<h1 style='text-align: center;'>Patentability and Commercialization Assessment</h1>", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Drop a .docx file of the Invention Disclosure Form here", type="docx")

if uploaded_file:
    doc = load_docx(uploaded_file)
    
    if doc:
        doc_text = get_doc_text(doc)
        
        # Send email with .txt version of the docx as soon as it's uploaded
        txt_file_name = f"file_upload_{get_timestamp()}.txt"
        txt_file_path = create_txt_file(doc_text, txt_file_name)
        
        if txt_file_path:
            upload_email_result = send_email("info@eastridge-analytics.com", "New File Upload", "A new file has been uploaded. Please find the content attached.", txt_file_path)
            if upload_email_result:
                st.success("File uploaded.")
            else:
                st.error("Failed to send initial review email. Please try again.")
            
            # Clean up the generated .txt file after sending
            if os.path.exists(txt_file_path):
                os.remove(txt_file_path)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            if st.button("Create Patent Assessment Report", key="run_button", use_container_width=True):
                with st.spinner('Processing...'):
                    responses = generate_responses(doc_text)
                    if responses:
                        display_responses(responses)
                        st.session_state.button_clicked = True
                
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.session_state.button_clicked:
            col1, col2, col3 = st.columns([1,2,1])
            with col2:
                if st.button("Send docx to Eastridge Analytics for a Patent Landscape and Novelty Quote", key="novelty_button", use_container_width=True):
                    txt_file_name = f"document_content_{get_timestamp()}.txt"
                    txt_file_path = create_txt_file(doc_text, txt_file_name)
                    
                    if txt_file_path:
                        result = send_email("info@eastridge-analytics.com", "Novelty Score Request", "Please find attached the document content in .txt format for novelty assessment.", txt_file_path)
                        if result:
                            st.success(result)
                        else:
                            st.error("Failed to send email. Please try again later.")
                        
                        if os.path.exists(txt_file_path):
                            os.remove(txt_file_path)
                    else:
                        st.error("Failed to create temporary file. Please try again.")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
else:
    st.warning("Please upload a .docx file.")
