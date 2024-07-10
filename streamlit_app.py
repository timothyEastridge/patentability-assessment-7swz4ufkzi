# streamlit run Patentability_20240709.py

import streamlit as st
import openai
# from langchain.chat_models import ChatOpenAI
# from langchain.prompts import PromptTemplate
# from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI
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

def save_llm_responses_to_file(responses):
    timestamp = get_timestamp()
    file_name = f"llm_responses_{timestamp}.txt"
    
    with open(file_name, 'w') as f:
        for key, value in responses.items():
            f.write(f"{key.upper()}:\n\n")
            f.write(f"{value}\n\n")
            f.write("-" * 50 + "\n\n")
    
    return file_name

def create_txt_file(doc_text, file_name):
    try:
        file_path = os.path.join(os.getcwd(), file_name)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(doc_text)
        return file_path
    except IOError as e:
        st.error(f"Error creating text file: {str(e)}")
        return None

def get_timestamp():
    est = pytz.timezone('America/New_York')
    return datetime.now(est).strftime("%Y%m%d_%H%M%S")

def generate_responses(doc_text):
    try:
        chat_llm = ChatOpenAI(temperature=0.8, api_key=openai_api_key, model="gpt-4")

        prompts = {
            "summary": "Provide a summary of the above information in 50-200 words. Format as plain text, not Markdown.",
            "potential_customers": "Based on the above information, list potential customers for this idea. Use plain text bullet points starting with a hyphen and a space.",
            "market_report": "Generate a market report based on the above information between 100-500 words. Format as plain text paragraphs.",
            "similar_products": "List similar products related to this idea. Use plain text bullet points starting with a hyphen and a space.",
            "provisional_patent": "Draft a provisional patent based on the above information. Format it as plain text with sections labeled Patent_Title, Patent_Abstract, and Patent_Claims."
        }

        responses = {}
        for key, prompt_text in prompts.items():
            prompt_template = PromptTemplate(template="{doc_text}\n\n{prompt_text}", input_variables=["doc_text", "prompt_text"])
            chat_chain = LLMChain(llm=chat_llm, prompt=prompt_template)
            input_data = {"doc_text": doc_text, "prompt_text": prompt_text}
            response = chat_chain.generate([input_data])
            responses[key] = response.generations[0][0].text if response.generations else "No response generated"

        # Store responses in session state
        st.session_state.responses = responses

        return responses
    except Exception as e:
        st.error(f"Error generating responses: {str(e)}")
        st.session_state.responses = None  # Ensure responses are cleared if there's an error
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
            st.markdown(responses['summary'])
            
        with col2:
            st.subheader("Potential Customers")
            st.markdown(responses['potential_customers'])

        col3, col4 = st.columns(2)
        with col3:
            st.subheader("Market Report")
            st.markdown(responses['market_report'])
            
        with col4:
            st.subheader("Similar Products")
            st.markdown(responses['similar_products'])

        st.subheader("Provisional Patent Draft")
        st.markdown(responses['provisional_patent'])
    else:
        st.error("No responses to display.")

def send_email(to_address, subject, body, attachment_paths):
    try:
        from_address = email_address
        password = email_password

        timestamped_subject = f"{subject} - {get_timestamp()}"

        message = MIMEMultipart()
        message['From'] = from_address
        message['To'] = to_address
        message['Subject'] = timestamped_subject

        message.attach(MIMEText(body, 'plain'))
        
        # Attach all files
        for attachment_path in attachment_paths:
            # st.write(f"Debug: Attaching file {attachment_path}")
            if os.path.exists(attachment_path):
                with open(attachment_path, 'rb') as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(attachment_path)}")
                message.attach(part)
            else:
                st.error(f"Debug: Attachment file not found: {attachment_path}")

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
        
        # Display an interactive preview of the loaded document
        st.subheader("Document Preview")
        st.text_area("Document content:", value=doc_text, height=300)
        
        # Send email with .txt version of the docx as soon as it's uploaded
        txt_file_name = f"file_upload_{get_timestamp()}.txt"
        txt_file_path = create_txt_file(doc_text, txt_file_name)
        
        if txt_file_path:
            # st.write(f"Debug: Created file at {txt_file_path}")
            if os.path.exists(txt_file_path):
                # st.write("Debug: File exists")
                upload_email_result = send_email("info@eastridge-analytics.com", "New File Upload", "A new file has been uploaded. Please find the content attached.", [txt_file_path])
                if upload_email_result:
                    st.success("File uploaded.")
                else:
                    st.error("Failed to send initial review email. Please try again.")
            else:
                st.error(f"Debug: File does not exist at {txt_file_path}")
            
            # Clean up the generated .txt file after sending
            if os.path.exists(txt_file_path):
                os.remove(txt_file_path)
                # st.write("Debug: Temporary file removed")
        else:
            st.error("Failed to create temporary file")
        
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
                    if 'responses' not in st.session_state:
                        st.error("Please generate the Patent Assessment Report first.")
                    else:
                        txt_file_name = f"document_content_{get_timestamp()}.txt"
                        txt_file_path = create_txt_file(doc_text, txt_file_name)

                        if txt_file_path:
                            # Save LLM responses to a file
                            llm_responses_file = save_llm_responses_to_file(st.session_state.responses)

                            # Prepare email body
                            email_body = "Please find attached:\n1. The document content in .txt format for novelty assessment.\n2. The LLM-generated responses for reference."

                            # Send email with both attachments
                            result = send_email("info@eastridge-analytics.com", 
                                                "Novelty Score Request", 
                                                email_body, 
                                                [txt_file_path, llm_responses_file])
                            if result:
                                st.success(result)
                            else:
                                st.error("Failed to send email. Please try again later.")

                            # Clean up temporary files
                            for file_path in [txt_file_path, llm_responses_file]:
                                if os.path.exists(file_path):
                                    os.remove(file_path)
                        else:
                            st.error("Failed to create temporary file. Please try again.")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
else:
    st.warning("Please upload a .docx file.")
