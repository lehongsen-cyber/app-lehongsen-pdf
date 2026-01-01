import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
import time
import zipfile
import io

# --- CẤU HÌNH GIAO DIỆN DOANH NGHIỆP ---
st.set_page_config(
    page_title="Hệ Thống Số Hóa Tài Liệu",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS CHO GIAO DIỆN ---
st.markdown("""
<style>
    body {font-family: 'Segoe UI', sans-serif;}
    h1 {color: #003366;}
    
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
    /* Chỉnh màu nút tải ZIP cho nổi bật */
    .download-btn {
        background-color: #28a745 !important;
        color: white !important;
    }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- LOGIC XỬ LÝ ---
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
        if img_data is None: return "ERROR", "File lỗi."

        image_part = {"mime_type": "image/png", "data": img_data}
        
        prompt = """
        Đặt tên file PDF theo QUY CHUẨN CÔNG TY.
        1. CẤU TRÚC: YY.MM.DD_LOAI_SoHieu_NoiDung_TrangThai.pdf
        2. QUY ĐỊNH:
           - YY.MM.DD: Năm (2 số cuối).Tháng.Ngày (Ví dụ: 25.12.31).
           - LOAI: Viết tắt in hoa (QD, TTr, CV, TB, GP, HD, BB, BC...).
           - SoHieu: Số hiệu (Ví dụ: 125-UBND, thay / bằng -).
           - NoiDung: Tiếng Việt không dấu, ngắn gọn, nối bằng gạch dưới '_'.
           - TrangThai: Mặc định 'Signed'.
        Chỉ trả về tên file.
        """
        
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
                                st.warning(f"⏳ Hệ thống đang bận. Chờ {s}s... (Lần {attempt+1})")
                                time.sleep(1)
                            st.info("🔄 Đang xử lý lại...")
                            continue
                    else:
                        return None, "Server quá tải."
                else:
                    return None, str(e)
    except Exception as e:
        return None, str(e)

# --- GIAO DIỆN ---
with st.sidebar:
    st.title("⚙️ CẤU HÌNH")
    st.markdown("---")
    with st.expander("🔑 Google API Key", expanded=True):
        api_key = st.text_input("Nhập Key:", type="password")
    st.info("ℹ️ Quy tắc: `YY.MM.DD`")
    st.caption("© Internal System")

st.title("🏢 HỆ THỐNG SỐ HÓA TÀI LIỆU")
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
            
            st.success(f"✅ Kết nối thành công. Đang xử lý...")
            progress_bar = st.progress(0)
            
            # Danh sách chứa các file thành công để nén ZIP
            success_files = []
            
            for i, uploaded_file in enumerate(uploaded_files):
                with st.container():
                    status_box = st.empty()
                    new_name, error_msg = process_company_rule(uploaded_file, api_key, active_model, status_box)
                    
                    if error_msg:
                        st.error(f"❌ {uploaded_file.name}: {error_msg}")
                    else:
                        status_box.empty()
                        
                        # Lưu file vào danh sách để tý nữa nén ZIP
                        uploaded_file.seek(0)
                        file_data = uploaded_file.read()
                        success_files.append((new_name, file_data))
                        
                        # Hiển thị thẻ kết quả (Vẫn giữ nút tải lẻ nếu cần gấp)
                        col_info, col_dl = st.columns([3, 1])
                        with col_info:
                            st.markdown(f"""
                            <div class="result-card">
                                <b>📄 Gốc:</b> {uploaded_file.name}<br>
                                <b style="color: #0056b3;">✅ Chuẩn:</b> {new_name}
                            </div>
                            """, unsafe_allow_html=True)
                        with col_dl:
                            st.write("")
                            # Nút tải lẻ (Lưu ý: Bấm cái này vẫn sẽ reload trang)
                            st.download_button(
                                label="⬇️ Tải lẻ",
                                data=file_data,
                                file_name=new_name,
                                mime='application/pdf',
                                key=f"dl_{i}",
                                help="Lưu ý: Bấm nút này trang sẽ tải lại."
                            )
                
                progress_bar.progress((i + 1) / len(uploaded_files))
            
            # --- XỬ LÝ NÉN ZIP (GIẢI PHÁP TẢI TẤT CẢ) ---
            if success_files:
                st.markdown("---")
                st.success("🎉 Xử lý hoàn tất! Bấm nút dưới để tải tất cả về một lần.")
                
                # Tạo file ZIP trong bộ nhớ
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for name, data in success_files:
                        zf.writestr(name, data)
                
                # Nút tải ZIP to đùng
                st.download_button(
                    label="📦 TẢI VỀ TẤT CẢ (ZIP) - KHÔNG BỊ RELOAD",
                    data=zip_buffer.getvalue(),
                    file_name="Ho_so_da_so_hoa.zip",
                    mime="application/zip",
                    type="primary",
                    use_container_width=True
                )
