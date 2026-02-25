import streamlit as st
import requests
from streamlit_lottie import st_lottie
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import re
import io
from markdown_pdf import MarkdownPdf, Section

# --- 1. PAGE SETUP & BRANDING ---
st.set_page_config(page_title="CruX | Instant Cheat Sheets", page_icon="⚡", layout="centered")

# --- CUSTOM CSS FOR SHAPES & GRAPHICS ---
# This adds a modern gradient card shape behind our title
st.markdown("""
<style>
    /* This forces the background to be Sky Blue and removes any dark artifacts */
    .stApp {
        background-color: #E3F2FD;
    }
    
    /* The Hero Card - Now in a professional Blue gradient */
    .hero-container {
        background: linear-gradient(135deg, #0D47A1 0%, #42A5F5 100%);
        padding: 40px;
        border-radius: 25px;
        text-align: center;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        margin-bottom: 30px;
    }
    
    .hero-title {
        font-size: 3.5rem !important;
        font-weight: 800;
        margin: 0;
        color: white !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    .hero-subtitle {
        font-size: 1.3rem;
        color: #E3F2FD !important;
        margin-top: 10px;
    }

    /* Styling the input box to look modern */
    .stTextInput input {
        border-radius: 15px !important;
        border: 2px solid #BBDEFB !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. LOAD ANIMATION GRAPHIC ---
def load_lottieurl(url):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# Loads a free, modern animation of a student/laptop
lottie_graphic = load_lottieurl("https://assets5.lottiefiles.com/packages/lf20_vnikrcia.json")

# --- 3. RENDER THE BEAUTIFUL HEADER ---
# We use columns to put the text and graphic side-by-side
col1, col2 = st.columns([2, 1], gap="large")

with col1:
    st.markdown("""
        <div class="hero-container">
            <h1 class="hero-title">⚡ CruX</h1>
            <p class="hero-subtitle">Turn hours of lectures into a 2-minute cheat sheet.</p>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("### Paste your YouTube link below to begin.")

with col2:
    if lottie_graphic:
        st_lottie(lottie_graphic, height=200, key="study_animation")
    else:
        st.image("https://cdn-icons-png.flaticon.com/512/3048/3048122.png", width=150) # Backup graphic

st.markdown("---")

# --- 4. GET API KEY INVISIBLE ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("⚠️ Secrets file not found. Please set up your .streamlit/secrets.toml file.")
    st.stop()

# --- 5. CORE LOGIC FUNCTIONS ---
def get_video_transcript(youtube_url):
    video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", youtube_url)
    if not video_id_match:
        return None, "Could not find a valid YouTube Video ID."
    
    video_id = video_id_match.group(1)
    
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)
        for transcript in transcript_list:
            raw_transcript = transcript.fetch().to_raw_data()
            full_transcript = " ".join([chunk['text'] for chunk in raw_transcript])
            return full_transcript, None
    except Exception as e:
        return None, f"Error: No captions found at all. Details: {e}"

def generate_cheat_sheet(transcript, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash') 
    
    prompt = """
    You are an expert university professor. Read the following lecture transcript and create a highly organized, easy-to-read 'Cheat Sheet' for a student cramming for an exam.
    
    Please format using Markdown and include:
    1. **Summary:** A 3-sentence summary of the main topic.
    2. **Core Concepts:** The top 5-7 core concepts explained simply.
    3. **Key Terms/Formulas:** Any important vocabulary, dates, or formulas mentioned.
    4. **Practice Exam:** 5 highly likely exam questions based on this material.
    5. **Answer Key:** Provide detailed, correct answers to the 5 practice questions you just generated. Put this at the very end.
    
    Here is the transcript:
    """
    response = model.generate_content([prompt, transcript])
    return response.text

# --- 6. INTERACTIVE USER INTERFACE ---
with st.container():
    youtube_url = st.text_input("🔗 YouTube Lecture Link:", placeholder="https://www.youtube.com/watch?v=...")
    generate_button = st.button("🚀 Generate Cheat Sheet", type="primary", use_container_width=True)

if generate_button:
    if not youtube_url:
        st.warning("⚠️ Please paste a YouTube link first!")
    else:
        with st.status("Initializing CruX...", expanded=True) as status:
            st.write("📥 Extracting lecture transcript...")
            transcript, error = get_video_transcript(youtube_url)
            
            if error:
                status.update(label="Extraction Failed", state="error", expanded=True)
                st.error(error)
            else:
                st.write("🧠 AI is analyzing core concepts...")
                try:
                    cheat_sheet = generate_cheat_sheet(transcript, API_KEY)
                    st.write("📝 Formatting cheat sheet and answer key...")
                    
                    pdf = MarkdownPdf(toc_level=0)
                    pdf.add_section(Section(cheat_sheet, toc=False))
                    pdf_buffer = io.BytesIO()
                    pdf.save_bytes(pdf_buffer)
                    
                    status.update(label="Cheat Sheet Ready!", state="complete", expanded=False)
                    st.balloons()
                    
                    st.markdown("---")
                    st.markdown(cheat_sheet)
                    st.markdown("---")
                    
                    st.download_button(
                        label="📥 Download Cheat Sheet (PDF)",
                        data=pdf_buffer.getvalue(),
                        file_name="CruX_CheatSheet.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    status.update(label="AI Processing Failed", state="error", expanded=True)
                    st.error(f"⚠️ AI Error: {e}")