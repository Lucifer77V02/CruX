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

st.markdown("""
<style>
    .stApp { background-color: #E3F2FD; }
    .hero-container {
        background: linear-gradient(135deg, #0D47A1 0%, #42A5F5 100%);
        padding: 40px; border-radius: 25px; text-align: center;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05); margin-bottom: 30px;
    }
    .hero-title { font-size: 3.5rem !important; font-weight: 800; color: white !important; }
    .hero-subtitle { font-size: 1.3rem; color: #E3F2FD !important; }
    .stTextInput input { border-radius: 15px !important; border: 2px solid #BBDEFB !important; }
</style>
""", unsafe_allow_html=True)

# --- 2. LOAD ANIMATION ---
def load_lottieurl(url):
    r = requests.get(url)
    return r.json() if r.status_code == 200 else None

lottie_graphic = load_lottieurl("https://assets5.lottiefiles.com/packages/lf20_vnikrcia.json")

# --- 3. HEADER ---
col1, col2 = st.columns([2, 1], gap="large")
with col1:
    st.markdown('<div class="hero-container"><h1 class="hero-title">⚡ CruX</h1><p class="hero-subtitle">Turn hours of lectures into a 2-minute cheat sheet.</p></div>', unsafe_allow_html=True)
    st.markdown("### Paste your YouTube link below to begin.")
with col2:
    if lottie_graphic: st_lottie(lottie_graphic, height=200)

st.markdown("---")

# --- 4. SECRETS ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    PROXY_KEY = st.secrets["WEBSCRAPING_AI_KEY"]
except KeyError:
    st.error("⚠️ API Keys missing in Streamlit Secrets!")
    st.stop()

# --- 5. CORE LOGIC ---
def get_video_transcript(youtube_url):
    video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", youtube_url)
    if not video_id_match: return None, "Invalid YouTube URL."
    video_id = video_id_match.group(1)
    
    SB_API_KEY = st.secrets["SCRAPINGBEE_API_KEY"]
    
    try:
        response = requests.get(
            url='https://app.scrapingbee.com',
            params={'api_key': SB_API_KEY, 'video_id': video_id}
        )
        
        # 1. Check if the request was successful
        if response.status_code == 200:
            # 2. Check if the response actually has content before parsing
            if not response.text.strip():
                return None, "API returned an empty response. (No transcript available?)"
            
            data = response.json()
            full_transcript = " ".join([chunk['text'] for chunk in data])
            return full_transcript, None
            
        else:
            # This identifies the real issue (e.g., 401 = Invalid Key, 402 = No Credits)
            return None, f"ScrapingBee Error {response.status_code}: {response.text[:100]}"
            
    except Exception as e:
        return None, f"Connection Error: {str(e)}"

def generate_cheat_sheet(transcript, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash') # Corrected model name
    prompt = f"Expert Professor: Create a Cheat Sheet from this transcript. Include Summary, Core Concepts, Key Terms, and a 5-question Practice Exam with Answer Key. \n\nTranscript: {transcript}"
    response = model.generate_content(prompt)
    return response.text

# --- 6. INTERFACE ---
youtube_url = st.text_input("🔗 YouTube Lecture Link:", placeholder="https://...")
generate_button = st.button("🚀 Generate Cheat Sheet", type="primary", use_container_width=True)

if generate_button:
    if not youtube_url:
        st.warning("⚠️ Paste a link first!")
    else:
        with st.status("Initializing CruX...", expanded=True) as status:
            st.write("📥 Extraction in progress (Residential Proxy)...")
            transcript, error = get_video_transcript(youtube_url)
            
            if error:
                status.update(label="Extraction Failed", state="error")
                st.error(error)
            else:
                st.write("🧠 AI Analyzing Lecture...")
                try:
                    cheat_sheet = generate_cheat_sheet(transcript, API_KEY)
                    
                    pdf = MarkdownPdf(toc_level=0)
                    pdf.add_section(Section(cheat_sheet))
                    pdf_buffer = io.BytesIO()
                    pdf.save_bytes(pdf_buffer)
                    
                    status.update(label="Ready!", state="complete")
                    st.balloons()
                    st.markdown(cheat_sheet)
                    st.download_button("📥 Download PDF", data=pdf_buffer.getvalue(), file_name="CruX_CheatSheet.pdf", mime="application/pdf")
                except Exception as e:
                    st.error(f"AI Error: {e}")
