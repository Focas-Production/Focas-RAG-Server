
import streamlit as st
import requests
import os
import io
import cv2
import numpy as np
from PIL import Image
import pytesseract
from google.cloud import documentai_v1 as documentai
import speech_recognition as sr 
import tempfile
from pydub import AudioSegment
import base64
from query import get_answer

# Load environment variables from .env.local
import os
# Read .env.local file directly
env_file_path = '.env.local'
if os.path.exists(env_file_path):
    with open(env_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                try:
                    key, value = line.split('=', 1)
                    # Handle URL encoding in values
                    value = value.replace('%40', '@').replace('%25', '%')
                    os.environ[key] = value
                except:
                    continue

# Set OpenAI API key directly if not already set
if not os.getenv('OPENAI_API_KEY'):
    os.environ['OPENAI_API_KEY'] = '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' 


# --- API Configuration ---
API_URL_SESSION = "http://localhost:5555/api/chat/session"
API_URL_MESSAGE = "http://localhost:5555/api/chat/message"
API_URL_EVALUATE = "http://localhost:5001/evaluate"

# --- Google Cloud Document AI Configuration ---
# IMPORTANT: Replace these with your actual Google Cloud Project details
GCP_PROJECT_ID = "your-gcp-project-id"
GCP_LOCATION = "us"  # or "eu"
GCP_PROCESSOR_ID = "your-processor-id"

# --- OpenAI Client Initialization ---
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- API Calling Functions ---
def get_answer_from_api(level, subject, query):
    try:
        session_payload = {"userId": "60c72b9f9b1d8f3b4c8b4567"}
        session_res = requests.post(API_URL_SESSION, json=session_payload, timeout=10)
        session_res.raise_for_status()
        session_data = session_res.json()
        session_id = session_data['_id']

        message_payload = {"sessionId": session_id, "userMessage": query}
        message_res = requests.post(API_URL_MESSAGE, json=message_payload, timeout=60)
        message_res.raise_for_status()
        return message_res.json()
    except Exception as e:
        return {"answer": f"Error connecting to backend API: {e}", "sources": []}

def evaluate_answer_from_api(user_answer, reference_answer):
    try:
        response = requests.post(API_URL_EVALUATE, json={"user_answer": user_answer, "reference_answer": reference_answer})
        response.raise_for_status()
        return response.json().get("evaluation", "No evaluation returned.")
    except Exception as e:
        return f"Error connecting to evaluation service: {e}"

# --- OCR Helper Functions ---
def layout_to_text(layout, text):
    """Extracts text from a Document AI layout object."""
    if not layout.text_anchor.text_segments:
        return ""
    return "".join(text[int(seg.start_index or 0):int(seg.end_index)] for seg in layout.text_anchor.text_segments)

def detect_handwriting_docai(image_pil):
    """Detects handwriting using Google Cloud Document AI."""
    client = documentai.DocumentProcessorServiceClient(
        client_options={"api_endpoint": f"{GCP_LOCATION}-documentai.googleapis.com"}
    )
    name = client.processor_path(GCP_PROJECT_ID, GCP_LOCATION, GCP_PROCESSOR_ID)

    img_bytes = io.BytesIO()
    image_pil.save(img_bytes, format="PNG")
    raw_doc = {"content": img_bytes.getvalue(), "mime_type": "image/png"}
    
    request = {"name": name, "raw_document": raw_doc}
    result = client.process_document(request=request)
    document = result.document

    return "\n".join(layout_to_text(block.layout, document.text).strip() for page in document.pages for block in page.blocks)

def is_handwritten(image_pil):
    """A simple heuristic to guess if an image contains mostly handwriting."""
    img_gray = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2GRAY)
    data = pytesseract.image_to_data(img_gray, output_type=pytesseract.Output.DICT)
    confs = [int(c) for c in data["conf"] if c != "-1"]
    avg_conf = np.mean(confs) if confs else 0
    return avg_conf < 60

# Helper: Convert image to Base64
def image_to_base64_str(image_pil):
    buf = io.BytesIO()
    image_pil.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

# GPT-4 Vision OCR
def extract_text_with_gpt4(image_pil):
    img_b64 = image_to_base64_str(image_pil)
    data_url = f"data:image/png;base64,{img_b64}"

    response = client.chat.completions.create(
        model="gpt-4o-mini",  # or "gpt-4o" if you want higher quality
        messages=[
            {"role": "system", "content": "You are an OCR system. Extract all text from the image as accurately as possible."},
            {"role": "user", "content": [
                {"type": "text", "text": "Please extract all the text from this image:"},
                {"type": "image_url", "image_url": {"url": data_url}}
            ]}
        ]
    )
    return response.choices[0].message.content.strip()

# --- Streamlit UI ---
st.set_page_config(page_title="CA AI Assistant", layout="wide")
st.title("📘 CA AI Assistant")

st.session_state.setdefault("evaluation_started", False)
st.session_state.setdefault("reference_answer", "")

level = st.selectbox("Select Level", ["Foundation", "Intermediate", "Final"])
subjects = {
    "Foundation": ["accounting", "business_economics", "business_law", "quantitative_aptitude"],
    "Intermediate": ["advanced_accounting", "auditing_and_ethics", "corporate_and_other_laws", "cost_and_management_accounting", "financial_management", "idt", "it", "strategic_management"],
    "Final": ["auditing"]
}
subject = st.selectbox("Select Subject", subjects[level])
input_mode = st.radio("Select Input Mode", ["Text", "Image", "Voice"])
query = ""

# --- Input Mode Logic ---
if input_mode == "Text":
    query = st.text_area("Ask your question from the selected PDF")

elif input_mode == "Image":
    uploaded_imgs = st.file_uploader("Upload image(s)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    extracted_texts = []
    if uploaded_imgs:
        for idx, file in enumerate(uploaded_imgs):
            img = Image.open(file)
            st.image(img, caption=f"Uploaded Image {idx+1}", width=500)
            try:
                text = extract_text_with_gpt4(img)
            except Exception as e:
                st.error(f"OCR failed: {e}")
                text = ""
            extracted_texts.append(text)
        query = "\n".join(extracted_texts)
        st.text_area("Extracted Text", query, height=300)

elif input_mode == "Voice":
    uploaded_audio = st.file_uploader("Upload your question as audio", type=["wav", "mp3", "m4a"])
    if uploaded_audio:
        recognizer = sr.Recognizer()
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_audio.type.split('/')[-1]}") as audio_temp:
            audio_temp.write(uploaded_audio.read())
            audio_input_path = audio_temp.name

        try:
            audio = AudioSegment.from_file(audio_input_path)
            pcm_wav_path = audio_input_path + "_converted.wav"
            audio.export(pcm_wav_path, format="wav")

            with sr.AudioFile(pcm_wav_path) as source:
                audio_data = recognizer.record(source)
                try:
                    query = recognizer.recognize_google(audio_data)
                    st.text_area("Recognized Question from Audio", query, height=200)
                except sr.UnknownValueError:
                    st.error("Could not understand the audio.")
                except sr.RequestError as e:
                    st.error(f"Google Speech API error: {e}")
        except Exception as e:
            st.error(f"Audio conversion or processing failed: {e}")
        finally:
            if os.path.exists(audio_input_path):
                os.remove(audio_input_path)
            if os.path.exists(pcm_wav_path):
                os.remove(pcm_wav_path)
    pass
# --- Action Mode Logic ---
mode = st.radio("Choose Mode", ["Get Answer", "Get Evaluated"])

if mode == "Get Answer":
    if st.button("Get Answer"):
        if not query.strip():
            st.warning("Please enter or extract a question.")
        else:
            with st.spinner("Thinking..."):
                response_data = get_answer_from_api(level, subject, query)
                st.success("Answer:")
                # st.write(response_data)
                st.write(response_data.get("answer", "No answer returned."))

# --- Get Evaluated Mode ---
elif mode == "Get Evaluated":
    if st.button("Start Evaluation (Get Correct Answer)"):
        if not query.strip():
            st.warning("Please enter a question first.")
        else:
            with st.spinner("Fetching correct answer..."):
                response_data = get_answer_from_api(level, subject, query)
                if "error" in response_data:
                    st.error(response_data["error"])
                else:
                    st.session_state.reference_answer = response_data.get("answer", "")
                    st.session_state.evaluation_started = True

    if st.session_state.evaluation_started:
        st.info("Correct Answer Loaded. Now, enter your answer below.")
        user_answer = st.text_area("Enter YOUR answer for evaluation:")
        
        if st.button("Evaluate My Answer"):
            if not user_answer.strip():
                st.warning("Please provide your answer to evaluate.")
            else:
                with st.spinner("Evaluating your answer..."):
                    evaluation_result = evaluate_answer_from_api(user_answer, st.session_state.reference_answer)
                    st.markdown("### Evaluation Result")
                    st.markdown(evaluation_result)