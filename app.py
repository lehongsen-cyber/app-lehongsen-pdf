import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF (Công nghệ chụp ảnh file)
import time

# --- CẤU HÌNH GIAO DIỆN DOANH NGHIỆP ---
st.set_page_config(
    page_title="Hệ Thống Số Hóa Tài Liệu",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS CHO GIAO DIỆN VĂN PHÒNG ---
st.markdown("""
<style>
    /* Font chữ nghiêm túc */
    body {font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;}
    h1 {color: #003366;} /* Màu xanh doanh nghiệp */
    
    /* Card kết quả */
    .result-card {
        background-color: #ffffff; 
        padding: 15px; 
        border: 1px solid #d1d1d1;
        border-radius: 5px;
        border-left: 5px solid #0056b3; 
        margin-bottom: 10px;
        color: #333333;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .stButton>button {
        background-color: #0056b3; 
        color: white; 
        border-radius: 4px; 
        height: 3em;
    }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- LOGIC XỬ LÝ (GIỮ NGUYÊN CÔNG NGHỆ TỐT NHẤT) ---
def get_best_model(api_key):
    genai.configure(api_key=api_key)
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name:
                return m.name
    except:
        return None
    return "models/gemini-1.5-flash"

def pdf_page_to_image(uploaded_file):
    try:
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        page = doc.load_page(0) 
        pix = page.get_pixmap(dpi=150)
        img_data = pix.tobytes("png")
        return img_data
    except Exception:
        return None

def process_company_rule(uploaded_file, api_key, model_name, status_container):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        uploaded_file.seek(0)
        img_data = pdf_page_to_image(uploaded_file)
        if img_data is None: return "ERROR", "File lỗi hoặc bị khóa."

        image_part = {"mime_type": "image/png", "data": img_data}
        
        # --- PROMPT THEO QUY TẮC CÔNG TY (YY.MM.DD) ---
        prompt = """
        Bạn là nhân viên văn thư chuyên nghiệp. Hãy đặt tên file theo QUY CHUẨN CÔNG TY.
        
        1. CẤU TRÚC: 
           YY.MM.DD_LOAI_SoHieu_NoiDung_TrangThai.pdf
        
        2. QUY ĐỊNH CHI TIẾT:
           - YY.MM.DD: Năm (2 số cuối).Tháng.Ngày (Ví dụ: 25.12.31). Dùng dấu chấm ngăn cách.
           - LOAI: Viết tắt in hoa (QD, TTr, CV, TB, GP, HD, BB, BC...).
           - SoHieu: Số hiệu văn bản. (Ví dụ: 125-UBND). Thay dấu gạch chéo '/' bằng gạch ngang '-'.
           - NoiDung: Tiếng Việt không dấu, ngắn gọn, nối bằng gạch dưới '_'.
           - TrangThai: Mặc định là 'Signed' (Đã ký). Nếu là bản thảo thì 'v01'.
        
        3. VÍ DỤ MẪU:
           - Input: Quyết định 125/UBND ngày 15/08/2025.
           - Output: 25.08.15_QD_125-UBND_Giao_dat_Dot1_Signed.pdf
           
        YÊU CẦU: Chỉ trả về duy nhất tên file kết quả.
        """
        
        # Cơ chế thử lại (Anti-429)
        max_retries = 5
        wait_time = 65
        
        for attempt in range(max_retries):
            try:
                result = model.generate_content([prompt, image_part])
                new_name = result.text.strip().replace("`", "")
                if not new_name.lower().endswith(".pdf"): new_name += ".pdf"
                return new_name, None
                
            except Exception as e:
                if "429" in str(e) or "Quota" in str(e) or "400" in str(e):
                    if attempt < max_retries - 1:
                        with status_container:
                            for s in range(wait_time, 0, -1):
                                st.warning(f"⏳ Hệ thống đang bận. Vui lòng chờ {s}s... (Lần {attempt+1})")
                                time.sleep(1)
                            st.info("🔄 Đang xử lý lại...")
                            continue
                    else:
                        return None, "Server quá tải, vui lòng thử lại sau."
                else:
                    return None, str(e)
                    
    except Exception as e:
        return None, str(e)

# --- GIAO DIỆN NGƯỜI DÙNG ---
with st.sidebar:
    st.title("⚙️ CẤU HÌNH")
    st.markdown("---")
    
    with st.expander("🔑 Google API Key", expanded=True):
        api_key = st.text_input("Nhập Key:", type="password")
    
    st.info("ℹ️ Quy tắc: `YY.MM.DD`\n\nVí dụ: `25.12.31_QD...`")
    st.markdown("---")
    st.caption("© Internal System - For Company Use Only")

# --- PHẦN CHÍNH ---
st.title("🏢 HỆ THỐNG SỐ HÓA TÀI LIỆU DOANH NGHIỆP")
st.markdown("##### Tiêu chuẩn: `YY.MM.DD_LOAI_SoHieu_NoiDung_Signed.pdf`")

uploaded_files = st.file_uploader("Tải tập tin lên (PDF)", type=['pdf'], accept_multiple_files=True)

if uploaded_files:
    if st.button("🚀 BẮT ĐẦU SỐ HÓA"):
        if not api_key:
            st.warning("⚠️ Vui lòng nhập API Key.")
        else:
            active_model = get_best_model(api_key)
            if not active_model:
                st.error("❌ Key không hợp lệ.")
                st.stop()
            
            st.success(f"✅ Kết nối thành công. Đang xử lý hồ sơ...")
            progress_bar = st.progress(0)
            
            for i, uploaded_file in enumerate(uploaded_files):
                with st.container():
                    status_box = st.empty()
                    # Gọi hàm xử lý công ty
                    new_name, error_msg = process_company_rule(uploaded_file, api_key, active_model, status_box)
                    
                    if error_msg:
                        st.error(f"❌ {uploaded_file.name}: {error_msg}")
                    else:
                        status_box.empty()
                        col_info, col_dl = st.columns([3, 1])
                        with col_info:
                            st.markdown(f"""
                            <div class="result-card">
                                <b>📄 Tên gốc:</b> {uploaded_file.name}<br>
                                <b style="color: #0056b3;">✅ Tên chuẩn:</b> {new_name}
                            </div>
                            """, unsafe_allow_html=True)
                        with col_dl:
                            st.write("")
                            uploaded_file.seek(0)
                            st.download_button(
                                label="⬇️ TẢI VỀ",
                                data=uploaded_file,
                                file_name=new_name,
                                mime='application/pdf',
                                key=f"dl_{i}",
                                use_container_width=True
                            )
                progress_bar.progress((i + 1) / len(uploaded_files))
            
            st.success("🎉 Hoàn tất quá trình số hóa!")
