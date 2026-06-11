import os
import sys
import base64
import datetime
import tempfile
import streamlit as st
import pymongo
from bson.objectid import ObjectId

# Force sys.path to include the project root so we can import 'app'
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.model.question import Question
from app.utils.pdf_generator import PDFGenerator
from app.utils.ocr_service import OCRService

# --- PAGE CONFIGURATION & STYLING ---
st.set_page_config(
    page_title="EduScribe Online - Exam Composer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium CSS Injection
st.markdown("""
<style>
    /* Global Styles */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #1e3799, #0c2461);
        color: white;
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .main-header h1 {
        margin: 0;
        font-size: 2.2rem;
        font-weight: 700;
        color: white;
    }
    .main-header p {
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
        opacity: 0.9;
        color: #dcdde1;
    }
    
    /* Status Badge styling */
    .status-badge {
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 15px;
    }
    .status-badge.online {
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    .status-badge.offline {
        background-color: #fff3cd;
        color: #856404;
        border: 1px solid #ffeeba;
    }
    
    /* Question Card Styling */
    .q-card-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #2f3640;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
    }
    
    /* Sidebar Title styling */
    .sidebar-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #2f3640;
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)


# --- MONGODB CONNECTION & OPERATIONS ---

@st.cache_resource
def get_mongo_client(uri):
    """Establishes and caches the MongoDB connection."""
    try:
        # 5-second timeout for server selection
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
        # Force a connection check
        client.admin.command('ping')
        return client, None
    except Exception as e:
        return None, str(e)

def init_db():
    """Initializes the database connection using Secrets or fallbacks."""
    # 1. Read connection string from secrets or env
    mongo_uri = None
    if "MONGODB_URI" in st.secrets:
        mongo_uri = st.secrets["MONGODB_URI"]
    elif "mongo" in st.secrets and "uri" in st.secrets["mongo"]:
        mongo_uri = st.secrets["mongo"]["uri"]
    else:
        mongo_uri = os.environ.get("MONGODB_URI")
        
    # 2. Connect
    if mongo_uri:
        client, err = get_mongo_client(mongo_uri)
        if client:
            return client["eduscribe"], "online"
        else:
            return None, f"error: {err}"
    else:
        return None, "no_credentials"

# Global DB state placeholders (lazy-loaded)
db = None
db_status = "offline"

def get_db_connection():
    """Lazy-loads and returns the database connection."""
    global db, db_status
    if db is None and db_status == "offline":
        db, db_status = init_db()
    return db, db_status

# --- DATABASE HELPER FUNCTIONS ---

def save_paper_to_mongodb(paper_id, metadata, questions):
    """Saves or updates an exam paper in MongoDB."""
    database, _ = get_db_connection()
    if database is None:
        return False, "Database is offline."
        
    doc = {
        "school_name": metadata["school_name"],
        "exam_name": metadata["exam_name"],
        "time_allowed": metadata["time_allowed"],
        "instructions": metadata["instructions"],
        "questions": questions,
        "last_saved": datetime.datetime.now(datetime.UTC)
    }
    
    try:
        if paper_id:
            database.exam_papers.update_one({"_id": ObjectId(paper_id)}, {"$set": doc})
            return True, paper_id
        else:
            result = database.exam_papers.insert_one(doc)
            return True, str(result.inserted_id)
    except Exception as e:
        return False, str(e)

def load_paper_from_mongodb(paper_id):
    """Loads a specific exam paper from MongoDB."""
    database, _ = get_db_connection()
    if database is None:
        return None
    try:
        doc = database.exam_papers.find_one({"_id": ObjectId(paper_id)})
        return doc
    except Exception:
        return None

def list_papers_from_mongodb():
    """Lists summary info of all saved exam papers in MongoDB."""
    database, _ = get_db_connection()
    if database is None:
        return []
    try:
        cursor = database.exam_papers.find({}, {"school_name": 1, "exam_name": 1, "last_saved": 1}).sort("last_saved", -1)
        return [{"id": str(doc["_id"]), "school_name": doc.get("school_name", "Unnamed"), "exam_name": doc.get("exam_name", "Unnamed"), "last_saved": doc.get("last_saved")} for doc in cursor]
    except Exception:
        return []


def get_puter_token():
    """Tries to read the Puter token from secrets or environment variables."""
    if "PUTER_TOKEN" in st.secrets:
        return st.secrets["PUTER_TOKEN"]
    elif "puter" in st.secrets and "token" in st.secrets["puter"]:
        return st.secrets["puter"]["token"]
    return os.environ.get("PUTER_TOKEN")

def call_puter_ai(prompt, system_instruction="You are an expert educational AI assistant.", model="gpt-4o-mini"):
    """Sends a chat completions request to Puter's OpenAI-compatible endpoint."""
    token = get_puter_token()
    if not token:
        return False, "Puter API token is missing. Please add `PUTER_TOKEN` in your Streamlit secrets."
        
    url = "https://api.puter.com/puterai/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    
    try:
        import requests
        response = requests.post(url, json=payload, headers=headers, timeout=25)
        
        if response.status_code == 200:
            response_json = response.json()
            if "choices" in response_json and len(response_json["choices"]) > 0:
                return True, response_json["choices"][0]["message"]["content"]
            return False, f"Unexpected API response format: {response_json}"
        else:
            try:
                err_msg = response.json().get("error", {}).get("message", "Unknown error")
            except Exception:
                err_msg = response.text
            return False, f"Puter AI Error (Status {response.status_code}): {err_msg}"
    except Exception as e:
        return False, f"Connection Failure: {str(e)}"

def parse_generated_questions(ai_response):
    """Robustly extracts and parses a JSON list of questions from AI response."""
    import json
    text = ai_response.strip()
    
    # Strip markdown block formatting if present
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return True, data
        elif isinstance(data, dict) and "questions" in data:
            return True, data["questions"]
        return False, "Parsed JSON was not a list of questions."
    except Exception as e:
        return False, f"JSON Parsing Error: {str(e)}. Response was: {ai_response[:250]}..."


# --- STATE INITIALIZATION ---

if "questions" not in st.session_state:
    st.session_state.questions = []
if "school_name" not in st.session_state:
    st.session_state.school_name = "EduScribe Academy"
if "exam_name" not in st.session_state:
    st.session_state.exam_name = "Mid-Term Examination"
if "time_allowed" not in st.session_state:
    st.session_state.time_allowed = "3 Hours"
if "instructions" not in st.session_state:
    st.session_state.instructions = "All questions are compulsory.\nThe marks intended for questions are given in brackets [ ].\nUse of calculators is not permitted."
if "current_paper_id" not in st.session_state:
    st.session_state.current_paper_id = None
if "next_q_id" not in st.session_state:
    st.session_state.next_q_id = 1


# --- COMPILATION HELPER ---

def compile_pdf_from_state(school_name, exam_name, time_allowed, instructions, questions):
    """Generates LaTeX code, compiles to PDF locally, and returns bytes."""
    temp_files = []
    latex_questions = []
    
    # 1. Decode base64 images and write them to temp files in the root folder
    for idx, q in enumerate(questions):
        image_path = None
        if q.get("image_base64"):
            try:
                img_name = q.get("image_name", "image.png")
                ext = img_name.split(".")[-1] if "." in img_name else "png"
                temp_filename = f"temp_q_{q['id']}.{ext}"
                img_data = base64.b64decode(q["image_base64"])
                with open(temp_filename, "wb") as f:
                    f.write(img_data)
                image_path = temp_filename
                temp_files.append(temp_filename)
            except Exception as e:
                st.error(f"Failed to extract image for Question {idx + 1}: {e}")
                
        latex_questions.append(Question(
            id_num=idx + 1,
            text=q["text"],
            marks=q["marks"],
            image_path=image_path
        ))
        
    total_marks = sum(q.marks for q in latex_questions)
    clean_instr = [line.strip() for line in instructions.split("\n") if line.strip()]
    
    # 2. Build context
    context = {
        "school_name": school_name,
        "exam_name": exam_name,
        "time_allowed": time_allowed,
        "max_marks": str(total_marks),
        "instructions": clean_instr,
        "questions": latex_questions
    }
    
    # 3. Generate Tex File
    generator = PDFGenerator()
    tex_filename = "exam_paper_output.tex"
    success, msg = generator.generate_tex(context, tex_filename)
    
    pdf_bytes = None
    tex_bytes = None
    pdf_filename = "exam_paper_output.pdf"
    compile_err = None
    
    if success:
        # Read generated tex bytes
        with open(tex_filename, "rb") as f:
            tex_bytes = f.read()
            
        # Try compiling to PDF
        pdf_success, pdf_msg = generator.compile_to_pdf(tex_filename)
        if pdf_success:
            if os.path.exists(pdf_filename):
                with open(pdf_filename, "rb") as f:
                    pdf_bytes = f.read()
        else:
            compile_err = pdf_msg
    else:
        compile_err = msg
        
    # Cleanup temp files
    for tf in temp_files:
        if os.path.exists(tf):
            try: os.remove(tf)
            except Exception: pass
            
    if os.path.exists(tex_filename):
        try: os.remove(tex_filename)
        except Exception: pass
        
    if os.path.exists(pdf_filename):
        try: os.remove(pdf_filename)
        except Exception: pass
        
    for ext in [".aux", ".log"]:
        f_log = "exam_paper_output" + ext
        if os.path.exists(f_log):
            try: os.remove(f_log)
            except Exception: pass
            
    return pdf_bytes, tex_bytes, compile_err


# --- APP INTERFACE RENDERING ---

# 1. Header Banner
st.markdown("""
<div class="main-header">
    <h1>EduScribe Online</h1>
    <p>Premium Web-based Question Paper Composer & Online Database Sync</p>
</div>
""", unsafe_allow_html=True)

# 2. DB Status indicators
database, db_status = get_db_connection()
if db_status == "online":
    st.markdown('<div class="status-badge online">🟢 Connected to MongoDB Online</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="status-badge offline">🟡 Running in Local Session Mode (Database Offline)</div>', unsafe_allow_html=True)
    if db_status == "no_credentials":
        st.info("💡 To persist papers online, configure your `MONGODB_URI` in **Streamlit Secrets** or local `.streamlit/secrets.toml`.")
    else:
        st.warning(f"⚠️ MongoDB connection failed: {db_status}. Using local memory state.")

# Create main two-column layout
col_main, col_sidebar = st.columns([3, 1], gap="medium")

with col_main:
    # A. Exam Details Section
    with st.expander("📝 Edit Exam Paper Metadata & Header", expanded=True):
        col_sch, col_ex = st.columns(2)
        with col_sch:
            st.session_state.school_name = st.text_input("School Name", value=st.session_state.school_name)
        with col_ex:
            st.session_state.exam_name = st.text_input("Exam Name", value=st.session_state.exam_name)
            
        col_time, col_dummy = st.columns([1, 1])
        with col_time:
            st.session_state.time_allowed = st.text_input("Time Allowed", value=st.session_state.time_allowed)
            
        st.session_state.instructions = st.text_area(
            "Instructions (one per line)", 
            value=st.session_state.instructions,
            help="Enter instructions. Separate distinct instructions using newlines."
        )

    # A2. AI Question Assistant Section
    with st.expander("🤖 AI Question Assistant (Powered by Puter)", expanded=False):
        # Check if puter token is available
        puter_token = get_puter_token()
        if not puter_token:
            st.warning("⚠️ Puter API Token is not configured. Add `PUTER_TOKEN` to your Streamlit secrets to enable AI generation.")
        else:
            st.markdown("Generate fresh exam questions with step-by-step LaTeX formatting using advanced AI models.")
            
            col_ai_subj, col_ai_type = st.columns(2)
            with col_ai_subj:
                ai_subject = st.selectbox(
                    "Subject", 
                    options=["Mathematics", "Physics", "Chemistry", "Biology", "General Science", "English Grammar", "Computer Science", "General Knowledge"]
                )
            with col_ai_type:
                ai_type = st.selectbox(
                    "Question Type", 
                    options=["Multiple Choice (MCQ)", "Short Answer", "Long/Detailed Answer", "Fill in the Blanks", "Numerical Problem"]
                )
                
            col_ai_topic, col_ai_diff = st.columns(2)
            with col_ai_topic:
                ai_topic = st.text_input("Topic / Concept", placeholder="e.g. Quadratic Equations, Photosynthesis, Python Lists")
            with col_ai_diff:
                ai_difficulty = st.select_slider("Difficulty Level", options=["Easy", "Medium", "Hard"])
                
            col_ai_cnt, col_ai_mrk, col_ai_mod = st.columns(3)
            with col_ai_cnt:
                ai_count = st.number_input("Count", min_value=1, max_value=5, value=3)
            with col_ai_mrk:
                ai_marks = st.number_input("Marks per Question", min_value=1, max_value=20, value=5)
            with col_ai_mod:
                ai_model = st.selectbox("AI Model", options=["gpt-4o-mini", "gpt-4o", "claude-3-5-sonnet"])
                
            if st.button("🤖 Generate Questions via AI", use_container_width=True):
                if not ai_topic.strip():
                    st.error("Please enter a Topic / Concept first.")
                else:
                    prompt = f"""
                    Generate exactly {ai_count} questions of the following type:
                    - Subject: {ai_subject}
                    - Topic: {ai_topic}
                    - Question Type: {ai_type}
                    - Difficulty: {ai_difficulty}
                    - Recommended Marks: {ai_marks}

                    Ensure any mathematical formulas, variables, equations, or scientific symbols are wrapped in standard LaTeX delimiters (e.g. use $...$ for inline math like $x^2 + y^2 = r^2$, and $$...$$ for block equations).

                    Return the response as a valid JSON list of objects. Each object must have these exact keys:
                    1. "text": a string containing the question text with proper LaTeX formatting.
                    2. "marks": an integer indicating the marks (use {ai_marks}).

                    Output ONLY the raw JSON array. Do not wrap the JSON in markdown formatting like ```json or ```, and do not add any comments or introductory text.
                    """
                    
                    with st.spinner("AI is thinking and generating questions..."):
                        success, response = call_puter_ai(
                            prompt, 
                            system_instruction="You are an expert examiner who writes clear, academically rigorous exam questions formatted in LaTeX JSON.",
                            model=ai_model
                        )
                        
                        if success:
                            parse_ok, parsed_qs = parse_generated_questions(response)
                            if parse_ok:
                                st.session_state.generated_questions = parsed_qs
                                st.success("Successfully generated questions! Select the ones you want below:")
                            else:
                                st.error(f"Failed to parse AI output: {parsed_qs}")
                                st.text_area("Raw AI Response", value=response, height=150)
                        else:
                            st.error(f"AI Generation Failed: {response}")
                            
            # If there are generated questions in state, display them
            if "generated_questions" in st.session_state and st.session_state.generated_questions:
                selected_indices = []
                st.markdown("### Generated Questions:")
                for idx, gq in enumerate(st.session_state.generated_questions):
                    with st.container(border=True):
                        # Checkbox for selection
                        is_selected = st.checkbox(
                            f"Select Question {idx+1} ({gq.get('marks', ai_marks)} Marks)",
                            value=True,
                            key=f"sel_ai_q_{idx}"
                        )
                        st.write(gq.get("text", ""))
                        if is_selected:
                            selected_indices.append(idx)
                            
                if st.button("📥 Add Selected Questions to Composer", use_container_width=True, type="primary"):
                    for idx in selected_indices:
                        gq = st.session_state.generated_questions[idx]
                        st.session_state.questions.append({
                            "id": st.session_state.next_q_id,
                            "text": gq.get("text", ""),
                            "marks": gq.get("marks", ai_marks),
                            "image_base64": None,
                            "image_name": None
                        })
                        st.session_state.next_q_id += 1
                    # Clear generated questions from state after adding
                    st.session_state.generated_questions = []
                    st.success("Questions added to composer!")
                    st.rerun()

    # B. Composer Section
    st.subheader("📚 Exam Composer")
    
    if not st.session_state.questions:
        st.info("No questions added yet. Click '➕ Add Manual Question' below or scan an image via OCR to get started.")
    
    # Loop and render question cards
    questions_to_delete = []
    
    for i, q in enumerate(st.session_state.questions):
        # Update IDs on the fly to remain sequential
        q["id"] = i + 1
        
        # Wrap each question inside a styled box
        with st.container(border=True):
            st.markdown(f'<div class="q-card-header">Question {q["id"]}</div>', unsafe_allow_html=True)
            
            # Question Text Input
            q_text = st.text_area(
                "Question Content / LaTeX Editor",
                value=q["text"],
                key=f"q_text_{q['id']}",
                placeholder="Type question here (supports LaTeX e.g. $x^2 + y^2 = r^2$)...",
                height=80
            )
            q["text"] = q_text
            
            # Real-time Preview Area
            if q["text"].strip():
                st.markdown("**Preview:**")
                st.write(q["text"])  # Streamlit auto-renders LaTeX between $ symbols
                
            col_m, col_img, col_del, col_ai = st.columns([1.5, 3, 2, 2])
            with col_m:
                q["marks"] = st.number_input(
                    "Marks",
                    min_value=1,
                    max_value=100,
                    value=int(q["marks"]),
                    key=f"q_marks_{q['id']}"
                )
                
            with col_img:
                # If there's an image base64, show the name/option to delete image
                if q.get("image_base64"):
                    st.caption(f"📎 Attached: {q.get('image_name', 'image.png')}")
                    # Convert base64 to bytes to display it
                    try:
                        img_bytes = base64.b64decode(q["image_base64"])
                        st.image(img_bytes, width=200)
                    except Exception:
                        st.error("Failed to render preview image.")
                        
                    if st.button("❌ Remove Image", key=f"q_delimg_{q['id']}"):
                        q["image_base64"] = None
                        q["image_name"] = None
                        st.rerun()
                else:
                    uploaded_file = st.file_uploader(
                        "Attach Image",
                        type=["png", "jpg", "jpeg"],
                        key=f"q_upload_{q['id']}"
                    )
                    if uploaded_file is not None:
                        # Convert uploaded file to base64
                        bytes_data = uploaded_file.read()
                        base64_data = base64.b64encode(bytes_data).decode("utf-8")
                        q["image_base64"] = base64_data
                        q["image_name"] = uploaded_file.name
                        st.rerun()
                        
            with col_del:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if st.button("🗑️ Delete Question", key=f"q_del_{q['id']}", type="secondary", use_container_width=True):
                    questions_to_delete.append(i)
                    
            with col_ai:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                puter_token = get_puter_token()
                btn_ai_enhance = st.button(
                    "🪄 AI Enhance", 
                    key=f"q_ai_{q['id']}", 
                    disabled=not puter_token,
                    help="Automatically format equations to LaTeX and improve question grammar."
                )
                if btn_ai_enhance:
                    if not q["text"].strip():
                        st.toast("Question content is empty!")
                    else:
                        with st.spinner("AI Enhancing..."):
                            prompt = f"Format and improve this exam question. Wrap any mathematical symbols, variables, or equations in standard LaTeX notation ($...$). Clean up the grammar. Return ONLY the enhanced question text, without any explanation, intro, or comments.\n\nQuestion to enhance:\n{q['text']}"
                            success, response = call_puter_ai(
                                prompt,
                                system_instruction="You are an expert LaTeX editor. You return only the formatted question with standard LaTeX inline math delimiters, preserving the original question's content."
                            )
                            if success:
                                q["text"] = response.strip()
                                st.toast("Question enhanced successfully!")
                                st.rerun()
                            else:
                                st.error(f"AI Enhance failed: {response}")

    # Perform Deletions
    if questions_to_delete:
        for index in reversed(questions_to_delete):
            st.session_state.questions.pop(index)
        st.rerun()

    # Composer bottom controls
    st.markdown("---")
    col_add, col_ocr = st.columns(2)
    with col_add:
        if st.button("➕ Add Manual Question", use_container_width=True, type="primary"):
            st.session_state.questions.append({
                "id": st.session_state.next_q_id,
                "text": "",
                "marks": 1,
                "image_base64": None,
                "image_name": None
            })
            st.session_state.next_q_id += 1
            st.rerun()
            
    with col_ocr:
        # File uploader for OCR
        ocr_file = st.file_uploader(
            "📷 Drag/Upload Question Image for OCR Scan",
            type=["png", "jpg", "jpeg"],
            key="ocr_uploader",
            help="Extracts text/math formulas from images using Mathpix."
        )
        if ocr_file is not None:
            # We save it temporarily to send it to OCR service
            with st.spinner("Analyzing image via OCR..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix="." + ocr_file.name.split(".")[-1]) as tmp:
                    tmp.write(ocr_file.read())
                    tmp_path = tmp.name
                    
                try:
                    success, result = OCRService.extract_text(tmp_path)
                    if success:
                        st.session_state.questions.append({
                            "id": st.session_state.next_q_id,
                            "text": result,
                            "marks": 5, # default for complex scanned questions
                            "image_base64": None,
                            "image_name": None
                        })
                        st.session_state.next_q_id += 1
                        st.success("OCR successfully extracted and added question!")
                        # Wait a moment, then rerun to clear uploader
                        st.rerun()
                    else:
                        st.error(f"OCR Scan Failed: {result}")
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)


with col_sidebar:
    # Sidebar Area
    st.markdown('<div class="sidebar-title">Controls</div>', unsafe_allow_html=True)
    
    # 1. DATABASE MANAGEMENT SECTION (Only show if connected)
    if db_status == "online":
        st.markdown("### 💾 Online Storage")
        
        # A. Save Operation
        save_name = st.text_input("Name this exam paper:", value=st.session_state.exam_name)
        if st.button("💾 Save to Cloud", use_container_width=True):
            if not st.session_state.questions:
                st.error("Cannot save an empty paper. Add questions first.")
            else:
                with st.spinner("Syncing to MongoDB..."):
                    metadata = {
                        "school_name": st.session_state.school_name,
                        "exam_name": save_name,
                        "time_allowed": st.session_state.time_allowed,
                        "instructions": st.session_state.instructions
                    }
                    success, res_val = save_paper_to_mongodb(
                        st.session_state.current_paper_id,
                        metadata,
                        st.session_state.questions
                    )
                    
                    if success:
                        st.session_state.current_paper_id = res_val
                        st.session_state.exam_name = save_name
                        st.success("Paper successfully synced online!")
                    else:
                        st.error(f"Failed to save: {res_val}")
                        
        st.markdown("---")
        
        # B. Load Operation
        st.markdown("### 📂 Load from Cloud")
        saved_papers = list_papers_from_mongodb()
        if saved_papers:
            paper_options = {f"{p['school_name']} - {p['exam_name']} ({p['last_saved'].strftime('%Y-%m-%d %H:%M')})": p["id"] for p in saved_papers}
            selected_paper_str = st.selectbox("Select saved paper:", options=list(paper_options.keys()))
            
            if st.button("📂 Load Selected Paper", use_container_width=True):
                selected_id = paper_options[selected_paper_str]
                paper_data = load_paper_from_mongodb(selected_id)
                if paper_data:
                    st.session_state.current_paper_id = str(paper_data["_id"])
                    st.session_state.school_name = paper_data.get("school_name", "")
                    st.session_state.exam_name = paper_data.get("exam_name", "")
                    st.session_state.time_allowed = paper_data.get("time_allowed", "")
                    st.session_state.instructions = paper_data.get("instructions", "")
                    st.session_state.questions = paper_data.get("questions", [])
                    # Update next question id
                    max_id = max([q["id"] for q in st.session_state.questions]) if st.session_state.questions else 0
                    st.session_state.next_q_id = max_id + 1
                    st.success("Paper loaded successfully!")
                    st.rerun()
        else:
            st.caption("No papers saved online yet.")
            
        st.markdown("---")

    # 2. COMPILATION & DOWNLOADS
    st.markdown("### 🖨️ Generate & Export")
    
    # Calculate Total Marks
    total_marks = sum(q["marks"] for q in st.session_state.questions)
    st.metric(label="Total Marks", value=f"{total_marks} Marks")
    
    if st.button("⚙️ Compile Output", use_container_width=True, type="primary"):
        if not st.session_state.questions:
            st.warning("Composer is empty. Please add questions first.")
        else:
            with st.spinner("Compiling document template..."):
                pdf_bytes, tex_bytes, compile_err = compile_pdf_from_state(
                    st.session_state.school_name,
                    st.session_state.exam_name,
                    st.session_state.time_allowed,
                    st.session_state.instructions,
                    st.session_state.questions
                )
                
                if tex_bytes:
                    st.session_state.compiled_tex = tex_bytes
                    st.success("LaTeX generation successful!")
                else:
                    st.error("Failed to generate LaTeX template.")
                    
                if pdf_bytes:
                    st.session_state.compiled_pdf = pdf_bytes
                    st.success("PDF compiled successfully!")
                else:
                    st.session_state.compiled_pdf = None
                    if compile_err:
                        st.warning(f"PDF compilation skipped/failed:\n{compile_err}")
                        st.info("💡 You can still download the generated LaTeX (.tex) file below to compile locally.")
                        
    # Download Buttons (Conditional based on compiled state)
    if "compiled_pdf" in st.session_state and st.session_state.compiled_pdf:
        st.download_button(
            label="📥 Download PDF Document",
            data=st.session_state.compiled_pdf,
            file_name=f"{st.session_state.exam_name.replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        
    if "compiled_tex" in st.session_state and st.session_state.compiled_tex:
        st.download_button(
            label="📥 Download LaTeX Source (.tex)",
            data=st.session_state.compiled_tex,
            file_name=f"{st.session_state.exam_name.replace(' ', '_')}.tex",
            mime="text/plain",
            use_container_width=True
        )

    # 3. CLEAR ALL
    st.markdown("---")
    st.markdown("### 🗑️ Reset Compose")
    confirm_clear = st.checkbox("Confirm Reset")
    if st.button("🗑️ Clear All Composer State", use_container_width=True, disabled=not confirm_clear):
        st.session_state.questions = []
        st.session_state.current_paper_id = None
        st.session_state.next_q_id = 1
        st.success("Composer reset completed.")
        st.rerun()
