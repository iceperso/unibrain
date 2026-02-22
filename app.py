import streamlit as st
import easyocr
from PIL import Image
import numpy as np
from googletrans import Translator
from transformers import pipeline
import random
import io

# --- استدعاء مكتبات الملفات ---
import PyPDF2
import docx
from pptx import Presentation

# --- 1. إعدادات الواجهة ---
st.set_page_config(page_title="UniBrain Pro Max", page_icon="🎓", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .stButton>button { border-radius: 8px; background-color: #0d6efd; color: white; width: 100%; }
    .stButton>button:hover { background-color: #0b5ed7; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. تحميل المحركات ---
@st.cache_resource
def load_models():
    reader = easyocr.Reader(['ar', 'en'], gpu=False)
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    translator = Translator()
    return reader, summarizer, translator

reader, summarizer, translator = load_models()

# --- 3. دوال التعامل مع الملفات (Import & Export) ---

def extract_text(file, file_name):
    """دالة ذكية تتعرف على نوع الملف وتستخرج النص منه"""
    text = ""
    ext = file_name.split('.')[-1].lower()
    
    try:
        if ext in ['png', 'jpg', 'jpeg']:
            img = Image.open(file)
            res = reader.readtext(np.array(img), detail=0)
            text = " ".join(res)
            
        elif ext == 'pdf':
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
                
        elif ext == 'docx':
            doc = docx.Document(file)
            for para in doc.paragraphs:
                text += para.text + "\n"
                
        elif ext == 'pptx':
            prs = Presentation(file)
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text += shape.text + "\n"
    except Exception as e:
        st.error(f"حدث خطأ أثناء قراءة الملف {file_name}")
        
    return text

def create_word_file(text, title="المستند الأكاديمي"):
    """دالة لتوليد ملف Word قابل للتحميل"""
    doc = docx.Document()
    doc.add_heading(title, 0)
    doc.add_paragraph(text)
    
    # حفظ الملف في الذاكرة لتنزيله
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# --- 4. واجهة التطبيق ---

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3143/3143460.png", width=80)
    st.title("UniBrain Pro Max")
    st.markdown("يدعم: الصور، PDF، Word، و PowerPoint")
    st.write("---")
    
    # تحديث رافع الملفات ليدعم كل الصيغ
    uploaded_files = st.file_uploader("📂 ارفع ملفاتك هنا", 
                                      type=['png', 'jpg', 'jpeg', 'pdf', 'docx', 'pptx'], 
                                      accept_multiple_files=True)
    
    if uploaded_files:
        st.success(f"تم رفع {len(uploaded_files)} ملفات")

# --- المحتوى الرئيسي ---
if uploaded_files:
    if 'full_text' not in st.session_state or st.session_state.get('file_count') != len(uploaded_files):
        st.session_state.full_text = ""
        st.session_state.file_count = len(uploaded_files)
        
        with st.spinner('جاري قراءة واستخراج البيانات من الملفات...'):
            for file in uploaded_files:
                extracted = extract_text(file, file.name)
                st.session_state.full_text += f"\n--- محتوى {file.name} ---\n" + extracted

    tab1, tab2, tab3 = st.tabs(["📄 النصوص المستخرجة والتصدير", "🧠 الشرح والتلخيص", "🌐 الترجمة"])

    with tab1:
        st.subheader("النص الكامل من جميع الملفات")
        st.text_area("يمكنك مراجعة النص وتعديله هنا:", st.session_state.full_text, height=300)
        
        st.markdown("### 📥 تصدير الملفات (Export)")
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            st.download_button(label="💾 تحميل كملف نصي (.txt)", 
                               data=st.session_state.full_text, 
                               file_name="UniBrain_Extract.txt", mime="text/plain")
        with col_dl2:
            word_file = create_word_file(st.session_state.full_text, "النصوص المستخرجة - UniBrain")
            st.download_button(label="📝 تحميل كملف Word (.docx)", 
                               data=word_file, 
                               file_name="UniBrain_Extract.docx", 
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            st.caption("يمكنك رفع هذا الملف مباشرة إلى Canva لتصميمه.")

    with tab2:
        st.subheader("التلخيص الذكي")
        if st.button("توليد التلخيص"):
            if len(st.session_state.full_text.split()) > 30:
                with st.spinner("جاري تحليل المحتوى..."):
                    summary = summarizer(st.session_state.full_text[:2000], max_length=200, min_length=50, do_sample=False)
                    st.success("الخلاصة:")
                    st.write(summary[0]['summary_text'])
                    
                    # زر تحميل التلخيص كـ Word
                    sum_word = create_word_file(summary[0]['summary_text'], "التلخيص الذكي")
                    st.download_button("📝 تحميل التلخيص كملف Word", data=sum_word, file_name="Summary.docx")
            else:
                st.warning("المحتوى قصير جداً.")

    with tab3:
        st.subheader("الترجمة الأكاديمية")
        target_lang = st.radio("اختر لغة الترجمة:", ["العربية", "English"])
        if st.button("ترجم المحتوى"):
            dest = 'ar' if target_lang == "العربية" else 'en'
            with st.spinner("جاري الترجمة..."):
                translated = translator.translate(st.session_state.full_text[:2000], dest=dest)
                st.info(translated.text)

else:
    # شاشة الترحيب
    st.markdown("<br><br><h2 style='text-align: center; color: #6c757d;'>👈 ابدأ برفع ملفاتك من القائمة الجانبية</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #adb5bd;'>ارفع محاضراتك بصيغة PDF, Word, PowerPoint أو حتى صور الملازم.</p>", unsafe_allow_html=True)
    