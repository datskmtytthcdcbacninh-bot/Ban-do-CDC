import sys
import datetime
import json
import re

try:
    import pandas as pd
    import requests
    import fitz  # PyMuPDF xử lý PDF trên RAM
    import google.generativeai as genai
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except ImportError as e:
    print(f"\n[LỖI THIẾU THƯ VIỆN] Cần chạy lệnh trên CMD: pip install google-generativeai PyMuPDF gspread oauth2client pandas requests")
    input("\nNhấn Enter để thoát...")
    sys.exit()

# ==========================================
# CẤU HÌNH HỆ THỐNG
# ==========================================
GEMINI_API_KEY = "AQ.Ab8RN6JwwpMKJPJnxI5vlyPanzoqZtUzbik8oolcMGIHZQ4VZw"
SHEET_ID = "1h3E_zwJ4Fu22el6Gl-z8xYooshzXYsewKwOEY_FNOKA"
TAB_FORM_GID = "1656038969"  
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={TAB_FORM_GID}"
TAB_DESTINATION = "Dữ liệu Nội Kiểm" 

# Khởi tạo Google Gemini chuẩn SDK chính thức
genai.configure(api_key=GEMINI_API_KEY)
# Sử dụng model flash ổn định mới nhất
model = genai.GenerativeModel('gemini-1.5-flash')

def ghi_log_loi(thong_bao, loai_loi="SỰ CỐ"):
    with open("nhat_ky_loi_noi_kiem.txt", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] [{loai_loi}] {thong_bao}\n")

def ket_noi_google_sheets():
    """Kết nối ghi dữ liệu vào tab Dữ liệu Nội Kiểm"""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID)
        return sheet.worksheet(TAB_DESTINATION)
    except Exception as e:
        return None

def tai_va_chuyen_doi_pdf_thanh_anh_ram(gdrive_url):
    """Tải PDF/Ảnh từ Drive và render thành ảnh PNG sạch trên RAM bằng PyMuPDF"""
    try:
        file_id = gdrive_url.split("id=")[1]
        direct_url = f"https://drive.google.com/uc?id={file_id}&export=download"
        
        response = requests.get(direct_url)
        if response.status_code != 200:
            ghi_log_loi(f"Không tải được file từ Drive. Mã lỗi: {response.status_code}", "LỖI DRIVE")
            return None
            
        file_bytes = response.content
        
        # Nếu là PDF, dùng fitz render trực tiếp trang 1 thành ảnh chuẩn RGB
        if file_bytes.startswith(b'%PDF'):
            print("-> Đang render file PDF thành ảnh chuẩn trên RAM...")
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            page = doc.load_page(0)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # Zoom 2x nét chữ
            image_bytes = pix.tobytes("png")
        else:
            print("-> Đang xử lý file ảnh trực tiếp...")
            image_bytes = file_bytes
            
        return image_bytes
    except Exception as e:
        ghi_log_loi(f"Lỗi xử lý file RAM: {e}", "LỖI HỆ THỐNG")
        return None

def goi_gemini_phan_tich(image_bytes):
    """Sử dụng SDK chính thức của Google để gửi ảnh lên AI phân tích"""
    prompt = """
    Bạn là chuyên gia phân tích chất lượng nước. Hãy đọc ảnh phiếu xét nghiệm này. 
    Trích xuất kết quả các chỉ tiêu xét nghiệm và trả về DUY NHẤT một chuỗi JSON hợp lệ theo cấu trúc sau, tuyệt đối không kèm văn bản nào khác:
    {"ket_qua": [{"chi_tieu": "pH", "ket_qua_do": "7.2"}, {"chi_tieu": "Độ đục", "ket_qua_do": "0.5"}]}
    """
    try:
        # Đóng gói dữ liệu ảnh theo chuẩn SDK Google GenAI
        image_part = {
            "mime_type": "image/png",
            "data": image_bytes
        }
        
        response = model.generate_content([prompt, image_part])
        raw_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(raw_text)
    except Exception as e:
        ghi_log_loi(f"Lỗi AI Gemini SDK: {e}", "LỖI AI GEMINI")
        return None

def chay_he_thong_tu_dong():
    print("🚀 Bắt đầu quét Google Sheets để tìm báo cáo mới...")
    try:
        df = pd.read_csv(CSV_URL)
    except Exception as e:
        print(f"Không thể đọc Sheets. Vui lòng kiểm tra lại quyền Share file.")
        return

    if df.empty:
        print("Trang tính đang trống.")
        return

    worksheet = ket_noi_google_sheets()

    for index, row in df.iterrows():
        if len(row) < 6: continue
        
        thoi_gian_nop = str(row.iloc[0])
        ten_don_vi = str(row.iloc[1]) 
        ky_bao_cao = f"{row.iloc[2]} {row.iloc[3]}" 
        link_file = str(row.iloc[5])

        if pd.isna(link_file) or "drive.google.com" not in link_file:
            continue
            
        print(f"\n--- Đang xử lý: {ten_don_vi} - {ky_bao_cao} ---")
        
        # 1. Render file trên RAM
        img_bytes = tai_va_chuyen_doi_pdf_thanh_anh_ram(link_file)
        if not img_bytes: continue
            
        # 2. Gọi AI bóc tách
        print("Đang nhờ Google Gemini AI phân tích dữ liệu...")
        ai_data = goi_gemini_phan_tich(img_bytes)
        if not ai_data or "ket_qua" not in ai_data: 
            print("❌ Không thể đọc được dữ liệu từ file này.")
            continue

        so_mau_dat, so_mau_khong_dat = 0, 0
        chi_tiet_loi = []
        
        for item in ai_data["ket_qua"]:
            kq = str(item.get('ket_qua_do', '')).lower()
            if 'kph' in kq or 'không' in kq:
                so_mau_dat += 1
            else:
                try:
                    val = float(re.search(r'[-+]?\d*\.\d+|\d+', kq).group())
                    if val > 5:  # Ngưỡng mẫu giả định kiểm tra lỗi
                        so_mau_khong_dat += 1
                        chi_tiet_loi.append(f"{item.get('chi_tieu')} ({kq})")
                    else:
                        so_mau_dat += 1
                except:
                    so_mau_dat += 1

        danh_gia_chung = "🔴 KHÔNG ĐẠT" if so_mau_khong_dat > 0 else "🟢 ĐẠT"
        
        # 3. Đóng gói kết quả
        dong_du_lieu = [
            thoi_gian_nop,
            ten_don_vi,
            ky_bao_cao,
            so_mau_dat + so_mau_khong_dat, 
            so_mau_dat,
            so_mau_khong_dat,
            ", ".join(chi_tiet_loi) if chi_tiet_loi else "Không có lỗi",
            danh_gia_chung
        ]
        
        # 4. Ghi thẳng vào Google Sheets (tab Dữ liệu Nội Kiểm)
        if worksheet:
            worksheet.append_row(dong_du_lieu)
            print(f"✅ Đã tự động ghi kết quả của '{ten_don_vi}' vào tab '{TAB_DESTINATION}' thành công!")
        else:
            print("📌 Dữ liệu tổng hợp (Chưa cấu hình credentials.json để ghi Sheets):", dong_du_lieu)

if __name__ == "__main__":
    print("========================================================")
    print("   HỆ THỐNG XỬ LÝ NỘI KIỂM (GOOGLE GEMINI OFFICIAL SDK)  ")
    print("========================================================")
    chay_he_thong_tu_dong()
    print("\n========================================================")
    input("HOÀN THÀNH. Nhấn phím Enter để đóng cửa sổ...")