import pandas as pd
import streamlit as st
import folium
from folium.features import DivIcon
from streamlit_folium import st_folium
from streamlit_autorefresh import st_autorefresh
from utils import load_google_sheet, clean_name
import glob
import json
import os
import time
from shapely.geometry import shape
import threading
from datetime import datetime

# ==========================================
# HÀM GHI NHẬT KÝ RA MÀN HÌNH CMD (LOGGING)
# ==========================================
def in_log(tin_nhan):
    thoi_gian_hien_tai = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    print(f"[{thoi_gian_hien_tai}] {tin_nhan}")

# ==========================================
# IMPORT MODULE ZALO
# ==========================================
try:
    from modules.zalo_engine import gui_tin_nhan_qua_zalo
except ImportError:
    st.error("⚠️ Không tìm thấy file modules/zalo_engine.py. Tính năng Zalo tạm thời bị vô hiệu hóa.")
    in_log("❌ Lỗi: Không tìm thấy file modules/zalo_engine.py")

# ==========================================
# HÀM GỌI SIÊU POPUP DESKTOP 
# ==========================================
def hien_popup_desktop_tuy_chinh(dia_ban, loai, mo_ta, thoi_gian, nguoi_bao, sdt_bao, nguon_phat_hien):
    def show_tkinter_popup():
        try:
            in_log(f"💻 Đang bật Popup cảnh báo trên màn hình Desktop cho: {dia_ban}...")
            import tkinter as tk
            from tkinter import font
            import winsound
            
            root = tk.Tk()
            root.title("🚨 HỆ THỐNG CẢNH BÁO CDC")
            root.attributes("-topmost", True)
            
            window_width, window_height = 550, 400 
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            x = int((screen_width / 2) - (window_width / 2))
            y = int((screen_height / 2) - (window_height / 2))
            root.geometry(f"{window_width}x{window_height}+{x}+{y}")
            
            root.configure(bg="#FFFFFF") 
            
            title_font = font.Font(family="Times New Roman", size=18, weight="bold")
            text_font = font.Font(family="Times New Roman", size=14)
            bold_font = font.Font(family="Times New Roman", size=14, weight="bold")
            
            header_frame = tk.Frame(root, bg="#FF4B4B", pady=15)
            header_frame.pack(fill="x")
            tk.Label(header_frame, text=f"🚨 SỰ CỐ TỪ: {nguon_phat_hien.upper()}", font=title_font, fg="white", bg="#FF4B4B").pack()
            
            content_frame = tk.Frame(root, bg="#FFFFFF", padx=30, pady=15)
            content_frame.pack(fill="both", expand=True)
            
            tk.Label(content_frame, text="📍 Đơn vị/Địa bàn:", font=bold_font, fg="#31333F", bg="#FFFFFF").grid(row=0, column=0, sticky="w", pady=5)
            tk.Label(content_frame, text=f"{dia_ban}", font=font.Font(family="Times New Roman", size=15, weight="bold"), fg="#FF4B4B", bg="#FFFFFF").grid(row=0, column=1, sticky="w", pady=5, padx=10)
            
            tk.Label(content_frame, text="🔥 Phân loại:", font=bold_font, fg="#31333F", bg="#FFFFFF").grid(row=1, column=0, sticky="w", pady=5)
            tk.Label(content_frame, text=f"{loai}", font=bold_font, fg="#FFA421", bg="#FFFFFF").grid(row=1, column=1, sticky="w", pady=5, padx=10)
            
            tk.Label(content_frame, text="📝 Mô tả:", font=bold_font, fg="#31333F", bg="#FFFFFF").grid(row=2, column=0, sticky="nw", pady=5)
            tk.Label(content_frame, text=f"{mo_ta}", font=text_font, fg="#31333F", bg="#FFFFFF", wraplength=350, justify="left").grid(row=2, column=1, sticky="w", pady=5, padx=10)
            
            tk.Label(content_frame, text="👤 Báo cáo:", font=bold_font, fg="#31333F", bg="#FFFFFF").grid(row=3, column=0, sticky="w", pady=5)
            tk.Label(content_frame, text=f"{nguoi_bao} - 📞 {sdt_bao}", font=bold_font, fg="#2980B9", bg="#FFFFFF").grid(row=3, column=1, sticky="w", pady=5, padx=10)
            
            tk.Label(content_frame, text="🕒 Thời gian:", font=bold_font, fg="#31333F", bg="#FFFFFF").grid(row=4, column=0, sticky="w", pady=5)
            tk.Label(content_frame, text=f"{thoi_gian}", font=text_font, fg="#7F8C8D", bg="#FFFFFF").grid(row=4, column=1, sticky="w", pady=5, padx=10)
            
            btn = tk.Button(root, text="✅ ĐÃ TIẾP NHẬN THÔNG TIN", font=bold_font, bg="#21C354", fg="white", activebackground="#1E9E45", activeforeground="white", command=root.destroy, relief="flat", borderwidth=0, highlightthickness=0, padx=20, pady=8, cursor="hand2")
            btn.pack(pady=(0, 20))
            
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            root.mainloop()
            in_log(f"💻 Người dùng đã đóng Popup của: {dia_ban}")
        except Exception as e:
            in_log(f"❌ Lỗi hiển thị Tkinter Popup: {e}")

    threading.Thread(target=show_tkinter_popup, daemon=True).start()

# ==========================================
# HÀM BÓC TÁCH DANH SÁCH NHẬN CẢNH BÁO 
# ==========================================
def lay_danh_sach_nguoi_nhan(df_contacts, loai_su_co, nguon_phat_hien=""):
    ds_nguoi_nhan = []
    if df_contacts is None or df_contacts.empty: return ds_nguoi_nhan
    loai_su_co_lower = str(loai_su_co).lower().strip()
    nguon_phat_hien_lower = str(nguon_phat_hien).lower().strip()
    target_col = None
    
    if "cấp nước" in nguon_phat_hien_lower:
        for col in df_contacts.columns:
            if "cấp nước" in str(col).lower():
                target_col = col; break
                
    if not target_col:
        for col in df_contacts.columns:
            if loai_su_co_lower in str(col).lower() or str(col).lower() in loai_su_co_lower:
                target_col = col; break
                
    if not target_col:
        for col in df_contacts.columns:
            for i in range(min(3, len(df_contacts))):
                val = str(df_contacts.iloc[i][col]).lower().strip()
                if val and val not in ['nan', 'none']:
                    if loai_su_co_lower in val or val in loai_su_co_lower or "cấp nước" in val:
                        target_col = col; break
            if target_col: break
        
    if target_col:
        in_log(f"🔍 Dò tìm danh bạ: Đã chốt gửi theo cột [{target_col}]")
        for i in range(len(df_contacts)):
            val = str(df_contacts.iloc[i][target_col]).strip()
            val_lower = val.lower()
            if val_lower not in ['nan', 'none', '', 'ngập lụt', 'dịch bệnh truyền nhiễm', 'tntt', 'tai nạn lao động', 'sự cố môi trường', 'khác', 'blđ khoa']:
                if val.endswith('.0'): val = val[:-2]
                if val.isdigit() and len(val) == 9 and not val.startswith('0'): val = '0' + val
                if val.isdigit() and len(val) >= 9:
                    ds_nguoi_nhan.append(val)
                
    return list(set(ds_nguoi_nhan))

def send_zalo_background_list(danh_sach_gui, tin_nhan):
    try:
        if not danh_sach_gui: 
            in_log("⚠️ Zalo bị hủy vì Danh sách gửi trống!")
            return
        in_log(f"🚀 Bắt đầu gửi tin nhắn Zalo tới {len(danh_sach_gui)} số: {danh_sach_gui}")
        payload = [(nguoi, tin_nhan) for nguoi in danh_sach_gui]
        gui_tin_nhan_qua_zalo(payload)
        in_log("✅ Đã hoàn thành gửi thông báo Zalo!")
    except Exception as e:
        in_log(f"❌ Lỗi Background Zalo: {e}")

# ==========================================
# GIAO DIỆN HỘP THOẠI CẢNH BÁO TRÊN WEB
# ==========================================
@st.dialog("🚨 BÁO ĐỘNG SỰ CỐ MỚI 🚨")
def show_alert_modal(dia_ban, loai, mo_ta, thoi_gian, ds_nhan, nguon_phat_hien):
    st.error(f"**🏢 Nguồn báo:** {nguon_phat_hien.upper()} | **📍 Địa bàn:** {dia_ban}")
    st.warning(f"**🔥 Phân loại:** {loai}")
    st.info(f"**📝 Mô tả:** {mo_ta}")
    st.caption(f"🕒 Thời gian ghi nhận: {thoi_gian}")
    st.success(f"🚀 Zalo đã tự động gửi cảnh báo đến: {', '.join(ds_nhan)}")
    
    st.markdown("---")
    if st.button("✅ Tôi đã nhận thông tin", use_container_width=True):
        st.rerun()

# ==========================================
# PHẦN 1: QUÉT SỰ CỐ (XÃ + TRẠM)
# ==========================================
def get_active_incidents(sheet_id):
    tram_incidents, xa_incidents = [], []
    in_log("🔄 Bắt đầu chu kỳ quét dữ liệu Google Sheets mới...")
    
    # 1. QUÉT SỰ CỐ TRẠM CẤP NƯỚC
    try:
        df_tram = load_google_sheet(sheet_id, "Sự cố đơn vị cấp nước")
        if not df_tram.empty:
            df_tram.columns = df_tram.columns.astype(str).str.strip()
            cols = list(df_tram.columns)
            
            idx_dv=1; idx_th=4; idx_loai=7; idx_tg=5; idx_bp=9; idx_mota=8; idx_nguoibao=2; idx_sdt=3; idx_link=4
            for i, c in enumerate(cols):
                c_low = str(c).lower().strip()
                if "người báo" in c_low or "họ tên" in c_low: idx_nguoibao = i
                elif "đơn vị" in c_low or "cấp nước" in c_low: idx_dv = i
                elif "tình trạng" in c_low or "tình hình" in c_low: idx_th = i
                elif "phân loại" in c_low or "loại" in c_low: idx_loai = i
                elif "thời gian" in c_low: idx_tg = i
                elif "biện pháp" in c_low or "xử lý" in c_low: idx_bp = i
                elif "mô tả" in c_low or "hiện trạng" in c_low or "chi tiết" in c_low: idx_mota = i
                elif "điện thoại" in c_low or "liên hệ" in c_low or "sđt" in c_low: idx_sdt = i
                elif "vị trí" in c_low or "địa điểm" in c_low: idx_link = i
                
            latest_tram_status = {}
            for index, row in df_tram.iterrows():
                ten_don_vi = str(row[cols[idx_dv]]).strip() if len(cols) > idx_dv else ""
                if not ten_don_vi or ten_don_vi.lower() in ['nan', 'none']: continue
                
                tinh_trang = str(row[cols[idx_th]]).strip().lower() if len(cols) > idx_th else ""
                loai_su_co = str(row[cols[idx_loai]]).strip() if len(cols) > idx_loai else "Sự cố"
                thoi_gian = str(row[cols[idx_tg]]).strip() if len(cols) > idx_tg else "Đang cập nhật"
                bien_phap = str(row[cols[idx_bp]]).strip() if len(cols) > idx_bp else "Đang xử lý"
                mo_ta = str(row[cols[idx_mota]]).strip() if len(cols) > idx_mota else "Không có thông tin thêm"
                nguoi = str(row[cols[idx_nguoibao]]).strip() if len(cols) > idx_nguoibao else "Chưa ghi nhận"
                sdt = str(row[cols[idx_sdt]]).strip() if len(cols) > idx_sdt else "Chưa ghi nhận"
                link = str(row[cols[idx_link]]).strip() if len(cols) > idx_link else ""
                
                if nguoi.lower() in ['nan', 'none', '']: nguoi = "Không cung cấp"
                if sdt.lower() in ['nan', 'none', '']: sdt = "Không cung cấp"
                if sdt.endswith('.0'): sdt = sdt[:-2]
                if sdt.isdigit() and len(sdt)==9 and not sdt.startswith('0'): sdt = '0'+sdt
                if link.lower() in ['nan', 'none', ''] or not link.startswith('http'): link = "https://bandocdc.bacninh.gov.vn"
                
                latest_tram_status[clean_name(ten_don_vi)] = {
                    "ten": ten_don_vi, "tinh_trang": tinh_trang, "loai": loai_su_co,
                    "thoi_gian": thoi_gian, "xu_ly": bien_phap, "mo_ta": mo_ta,
                    "nguoi_bao": nguoi, "sdt_bao": sdt, "link_zalo": link, "index": index
                }
            for info in latest_tram_status.values():
                if not any(w in info["tinh_trang"] for w in ["bình thường", "ổn định", "kết thúc", "xong"]):
                    if "sự cố" in info["tinh_trang"] or "sự kiện" in info["tinh_trang"] or info["tinh_trang"] != "":
                        tram_incidents.append(info)
        in_log(f"   -> Đọc tab Trạm Nước: Hiện có {len(tram_incidents)} trạm đang gặp sự cố.")
    except Exception as e: 
        in_log(f"❌ Lỗi load dữ liệu Trạm Cấp Nước: {e}")

    # 2. QUÉT SỰ CỐ XÃ 
    try:
        gid_su_co = "730159322"
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid_su_co}&t={int(time.time())}"
        df_xa = pd.read_csv(csv_url)
        
        if not df_xa.empty:
            df_xa.columns = df_xa.columns.astype(str).str.strip()
            cols = list(df_xa.columns)
            
            idx_dv=1; idx_th=2; idx_loai=6; idx_tg=3; idx_bp=9; idx_mota=7; idx_nguoibao=12; idx_sdt=13; idx_link=5
            for i, c in enumerate(cols):
                c_low = str(c).lower().strip()
                if "người báo" in c_low or "họ tên" in c_low: idx_nguoibao = i
                elif "địa bàn" in c_low: idx_dv = i
                elif "tình hình" in c_low or "tình trạng" in c_low: idx_th = i
                elif "phân loại" in c_low or "loại" in c_low: idx_loai = i
                elif "thời gian" in c_low: idx_tg = i
                elif "biện pháp" in c_low or "xử lý" in c_low: idx_bp = i
                elif "mô tả" in c_low: idx_mota = i
                elif "điện thoại" in c_low or "liên hệ" in c_low or "sđt" in c_low: idx_sdt = i
                elif "vị trí" in c_low or "link" in c_low: idx_link = i
                
            latest_xa_status = {}
            for index, row in df_xa.iterrows():
                ten_xa = str(row[cols[idx_dv]]).strip() if len(cols) > idx_dv else ""
                if not ten_xa or ten_xa.lower() in ['nan', 'none']: continue
                
                tinh_trang = str(row[cols[idx_th]]).strip().lower() if len(cols) > idx_th else ""
                loai_su_co = str(row[cols[idx_loai]]).strip() if len(cols) > idx_loai else "Sự cố"
                thoi_gian = str(row[cols[idx_tg]]).strip() if len(cols) > idx_tg else "Đang cập nhật"
                bien_phap = str(row[cols[idx_bp]]).strip() if len(cols) > idx_bp else "Đang xử lý"
                mo_ta = str(row[cols[idx_mota]]).strip() if len(cols) > idx_mota else "Không có thông tin thêm"
                nguoi = str(row[cols[idx_nguoibao]]).strip() if len(cols) > idx_nguoibao else "Chưa ghi nhận"
                sdt = str(row[cols[idx_sdt]]).strip() if len(cols) > idx_sdt else "Chưa ghi nhận"
                link = str(row[cols[idx_link]]).strip() if len(cols) > idx_link else ""
                
                if nguoi.lower() in ['nan', 'none', '']: nguoi = "Không cung cấp"
                if sdt.lower() in ['nan', 'none', '']: sdt = "Không cung cấp"
                if sdt.endswith('.0'): sdt = sdt[:-2]
                if sdt.isdigit() and len(sdt)==9 and not sdt.startswith('0'): sdt = '0'+sdt
                if link.lower() in ['nan', 'none', ''] or not link.startswith('http'): link = "https://bandocdc.bacninh.gov.vn"

                latest_xa_status[clean_name(ten_xa)] = {
                    "ten": ten_xa, "tinh_trang": tinh_trang, "loai": loai_su_co,
                    "thoi_gian": thoi_gian, "xu_ly": bien_phap, "mo_ta": mo_ta,
                    "nguoi_bao": nguoi, "sdt_bao": sdt, "link_zalo": link, "index": index, "row": row
                }
            for info in latest_xa_status.values():
                if not any(w in info["tinh_trang"] for w in ["bình thường", "ổn định", "kết thúc", "xong"]):
                    if "sự cố" in info["tinh_trang"] or "sự kiện" in info["tinh_trang"] or info["tinh_trang"] != "":
                        xa_incidents.append(info)
        in_log(f"   -> Đọc tab Sự Cố Xã: Hiện có {len(xa_incidents)} xã đang gặp sự cố.")
    except Exception as e: 
        in_log(f"❌ Lỗi load dữ liệu Xã: {e}")
    
    in_log("✅ Hoàn tất chu kỳ quét!")
    return tram_incidents, xa_incidents

# ==========================================
# PHẦN CHÍNH: BẢN ĐỒ VÀ ĐIỀU HÀNH
# ==========================================
TOA_DO_MAC_DINH = [21.15, 106.05]

def render_page():
    # --- KHỞI TẠO BỘ NHỚ LƯU SỐ GIÂY (Mặc định 30s) ---
    if "refresh_sec_suco" not in st.session_state:
        st.session_state.refresh_sec_suco = 30

    col1, col2, col3 = st.columns([3, 1.5, 1])
    with col1:
        st.header("🚨 Trung Tâm Giám Sát Sự Cố & Dịch Bệnh")
        st.caption("Hệ thống tự động cập nhật. Bật Windows Popup và Zalo cảnh báo.")
    
    with col2:
        st.write("") 
        # TẠO Ô NHẬP SỐ TỰ DO THAY CHO DROPDOWN
        refresh_sec = st.number_input(
            "⏱️ Tự động làm mới (giây):", 
            min_value=0, 
            value=st.session_state.refresh_sec_suco, 
            step=10,
            key="num_refresh_suco",
            help="Nhập số giây để bản đồ tự làm mới. Nhập số 0 để TẮT."
        )
        st.session_state.refresh_sec_suco = refresh_sec
    
    with col3:
        st.write("")
        st.write("") 
        if st.button("🔄 Làm mới ngay", use_container_width=True, key="btn_refresh_suco"):
            in_log("🔄 Người dùng vừa bấm nút LÀM MỚI THỦ CÔNG (Tab Y Tế)")
            st.cache_data.clear() 
            st.rerun()            

    # --- KÍCH HOẠT VÒNG LẶP THỜI GIAN ---
    if refresh_sec > 0:
        st_autorefresh(interval=refresh_sec * 1000, key="dashboard_autorefresh_suco")

    # =========================================================
    # FIX LỖI CACHE: Ép hệ thống xóa bộ nhớ đệm mỗi lần chạy lại 
    # =========================================================
    st.cache_data.clear()

    sheet_id = "1sIeZpXnwwJgRftbPVBfkOLRxLck0OjshNCVGkMe3W-k"

    tram_active, xa_active = get_active_incidents(sheet_id)
    
    if 'prev_xa_count' not in st.session_state:
        st.session_state.prev_xa_count = len(xa_active)
    if 'prev_tram_count' not in st.session_state:
        st.session_state.prev_tram_count = len(tram_active)

    trigger_alarm = False
    new_info = None
    nguon_phat_hien = ""

    if len(xa_active) > st.session_state.prev_xa_count:
        in_log(f"⚠️ CẢNH BÁO: Phát hiện số lượng Xã sự cố tăng lên (Từ {st.session_state.prev_xa_count} lên {len(xa_active)})")
        trigger_alarm = True
        new_info = xa_active[-1] 
        nguon_phat_hien = "Trạm Y Tế Xã"
    elif len(tram_active) > st.session_state.prev_tram_count:
        in_log(f"⚠️ CẢNH BÁO: Phát hiện số lượng Trạm sự cố tăng lên (Từ {st.session_state.prev_tram_count} lên {len(tram_active)})")
        trigger_alarm = True
        new_info = tram_active[-1]
        nguon_phat_hien = "Đơn Vị Cấp Nước"

    if trigger_alarm and new_info:
        dia_ban_moi = new_info['ten']
        loai_su_co_zalo = new_info['loai']
        mo_ta_zalo = new_info['mo_ta']
        thoi_gian_zalo = new_info['thoi_gian']
        nguoi_bao = new_info['nguoi_bao']
        sdt_bao = new_info['sdt_bao']
        link_zalo = new_info['link_zalo']

        ds_nhan = []
        try:
            df_contacts = load_google_sheet(sheet_id, "Danh sách nhận cảnh báo")
            ds_nhan = lay_danh_sach_nguoi_nhan(df_contacts, loai_su_co_zalo, nguon_phat_hien)
        except Exception as e: 
            in_log(f"❌ Lỗi đọc danh bạ Zalo: {e}")
        
        if not ds_nhan: 
            in_log("⚠️ Không tìm thấy người nhận theo Cột, tự động chuyển hướng gửi cho Lãnh đạo Khoa!")
            ds_nhan = ["0982518107"] 
            
        html_audio = """<audio autoplay><source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mpeg"></audio>"""
        st.markdown(html_audio, unsafe_allow_html=True)
        
        noi_dung_zalo = f"🚨 BÁO CÁO SỰ CỐ MỚI 🚨\n🏢 Nguồn báo: {nguon_phat_hien.upper()}\n📍 Đơn vị/Địa bàn: {dia_ban_moi}\n🔥 Phân loại: {loai_su_co_zalo}\n📝 Mô tả: {mo_ta_zalo}\n🕒 Thời gian: {thoi_gian_zalo}\n👤 Người báo: {nguoi_bao} ({sdt_bao})\n👉 Xem chi tiết tại: {link_zalo}"
        threading.Thread(target=send_zalo_background_list, args=(ds_nhan, noi_dung_zalo)).start()

        hien_popup_desktop_tuy_chinh(dia_ban_moi, loai_su_co_zalo, mo_ta_zalo, thoi_gian_zalo, nguoi_bao, sdt_bao, nguon_phat_hien)

        st.session_state.prev_xa_count = len(xa_active)
        st.session_state.prev_tram_count = len(tram_active)
        show_alert_modal(dia_ban_moi, loai_su_co_zalo, mo_ta_zalo, thoi_gian_zalo, ds_nhan, nguon_phat_hien)

    elif len(xa_active) < st.session_state.prev_xa_count:
        st.session_state.prev_xa_count = len(xa_active)
    elif len(tram_active) < st.session_state.prev_tram_count:
        st.session_state.prev_tram_count = len(tram_active)

    # =========================================================
    # VẼ BẢN ĐỒ Y TẾ - CHỈ VẼ CÁC SỰ CỐ CỦA XÃ 
    # =========================================================
    m = folium.Map(location=TOA_DO_MAC_DINH, zoom_start=10, tiles=None, control_scale=True)
    folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Bản đồ nền Xám', control=True).add_to(m)
    folium.TileLayer('https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google Maps', name='Bản đồ Giao thông', control=True, overlay=False).add_to(m)
    
    css = """
    <style>
    .radar-marker { width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid white; color: white; font-size: 15px; box-shadow: 0px 4px 6px rgba(0,0,0,0.3); }
    .radar-blue { background-color: #3498DB; animation: pulse-blue 1.5s infinite; } @keyframes pulse-blue { 0% {box-shadow: 0 0 0 0 rgba(52,152,219,0.7);} 70% {box-shadow: 0 0 0 15px rgba(52,152,219,0);} 100% {box-shadow: 0 0 0 0 rgba(52,152,219,0);} }
    .radar-purple { background-color: #9B59B6; animation: pulse-purple 1.5s infinite; } @keyframes pulse-purple { 0% {box-shadow: 0 0 0 0 rgba(155,89,182,0.7);} 70% {box-shadow: 0 0 0 15px rgba(155,89,182,0);} 100% {box-shadow: 0 0 0 0 rgba(155,89,182,0);} }
    .radar-orange { background-color: #E67E22; animation: pulse-orange 1.5s infinite; } @keyframes pulse-orange { 0% {box-shadow: 0 0 0 0 rgba(230,126,34,0.7);} 70% {box-shadow: 0 0 0 15px rgba(230,126,34,0);} 100% {box-shadow: 0 0 0 0 rgba(230,126,34,0);} }
    .radar-darkred { background-color: #C0392B; animation: pulse-darkred 1.5s infinite; } @keyframes pulse-darkred { 0% {box-shadow: 0 0 0 0 rgba(192,57,43,0.7);} 70% {box-shadow: 0 0 0 15px rgba(192,57,43,0);} 100% {box-shadow: 0 0 0 0 rgba(192,57,43,0);} }
    .radar-red { background-color: #E74C3C; animation: pulse-red 1.5s infinite; } @keyframes pulse-red { 0% {box-shadow: 0 0 0 0 rgba(231,76,60,0.7);} 70% {box-shadow: 0 0 0 15px rgba(231,76,60,0);} 100% {box-shadow: 0 0 0 0 rgba(231,76,60,0);} }
    </style>
    """
    m.get_root().html.add_child(folium.Element(css))
    
    xa_layer = folium.FeatureGroup(name="🗺️ Ranh giới xã", overlay=True, control=True, show=True)
    nhan_xa_layer = folium.FeatureGroup(name="🏷️ Tên các xã", overlay=True, control=True, show=False)
    su_co_layer = folium.FeatureGroup(name="🚨 Điểm cảnh báo", overlay=True, control=True, show=True)

    dynamic_centroids = {}
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    geojson_files = [f for f in glob.glob(os.path.join(data_dir, "*.geojson")) if "24_bac_ninh" not in f and "song_ngoi" not in f]
    
    for file_path in geojson_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f: geo_data = json.load(f)
            ten_hien_thi = os.path.splitext(os.path.basename(file_path))[0]
            clean_ten = clean_name(ten_hien_thi)
            folium.GeoJson(geo_data, style_function=lambda x: {"fillColor": "#D5D8DC", "color": "#7F8C8D", "weight": 1, "fillOpacity": 0.3}, tooltip=folium.Tooltip(ten_hien_thi)).add_to(xa_layer)
            for feature in geo_data.get("features", []):
                geom_type = feature.get("geometry", {}).get("type", "")
                if "Polygon" in geom_type:
                    geom = shape(feature["geometry"])
                    center_pt = geom.centroid
                    if not geom.contains(center_pt): center_pt = geom.representative_point()
                    dynamic_centroids[clean_ten] = [center_pt.y, center_pt.x]
                    html_content = f'<div style="font-size:10px; font-weight:bold; color:#2C3E50; text-align:center; text-shadow: 1px 1px 2px white, -1px -1px 2px white, 1px -1px 2px white, -1px 1px 2px white; pointer-events: none; width: 100px; transform: translate(-50%, -50%);">{ten_hien_thi}</div>'
                    folium.map.Marker([center_pt.y, center_pt.x], icon=DivIcon(icon_size=(0, 0), icon_anchor=(0, 0), html=html_content)).add_to(nhan_xa_layer)
                    break 
        except: pass
    
    su_co_active_count = 0
    for info in xa_active:
        row = info.get("row")
        if row is None: continue
        
        index = info["index"]
        dia_ban = info["ten"]
        
        cols = list(row.index)
        idx_diadiem=4; idx_anhhuong=8; idx_kinhdo=14; idx_vido=15
        for i, c in enumerate(cols):
            c_low = str(c).lower().strip()
            if "địa điểm" in c_low: idx_diadiem = i
            elif "số lượng" in c_low or "ảnh hưởng" in c_low: idx_anhhuong = i
            elif "kinh độ" in c_low: idx_kinhdo = i
            elif "vĩ độ" in c_low: idx_vido = i
        
        dia_diem = str(row[cols[idx_diadiem]]).strip() if len(cols) > idx_diadiem else "Chưa rõ"
        loai_su_co = info['loai']
        thoi_gian = info['thoi_gian']
        nguoi_anh_huong = str(row[cols[idx_anhhuong]]).strip() if len(cols) > idx_anhhuong else "Không rõ"
        if nguoi_anh_huong.lower() in ["nan", "none"]: nguoi_anh_huong = "Không rõ"
        bien_phap = info['xu_ly']
        nguoi_bao = info['nguoi_bao']
        sdt_bao = info['sdt_bao']

        su_co_lower = loai_su_co.lower()
        if "lụt" in su_co_lower or "nước" in su_co_lower: color_class, fa_icon, hex_color = "blue", "tint", "#3498DB"
        elif "dịch" in su_co_lower or "bệnh" in su_co_lower: color_class, fa_icon, hex_color = "purple", "bug", "#9B59B6"
        elif "môi trường" in su_co_lower or "rác" in su_co_lower: color_class, fa_icon, hex_color = "orange", "leaf", "#E67E22"
        elif "tai nạn" in su_co_lower or "thương tích" in su_co_lower: color_class, fa_icon, hex_color = "darkred", "ambulance", "#C0392B"
        else: color_class, fa_icon, hex_color = "red", "exclamation-triangle", "#E74C3C"

        coords = None
        kinh_do = str(row[cols[idx_kinhdo]]).strip() if len(cols) > idx_kinhdo else ""
        vi_do = str(row[cols[idx_vido]]).strip() if len(cols) > idx_vido else ""
        
        if kinh_do and vi_do and kinh_do.lower() not in ['nan', 'none'] and vi_do.lower() not in ['nan', 'none']:
            try: coords = [float(vi_do), float(kinh_do)]
            except: pass
            
        if not coords:
            dia_ban_clean = clean_name(dia_ban)
            for key_xa, toado_xa in dynamic_centroids.items():
                if key_xa in dia_ban_clean or dia_ban_clean in key_xa:
                    coords = [toado_xa[0] + (index * 0.0005), toado_xa[1] + (index * 0.0005)]; break

        if not coords: coords = [TOA_DO_MAC_DINH[0] + (index * 0.005), TOA_DO_MAC_DINH[1] + (index * 0.005)]
                
        su_co_active_count += 1
        maps_url = f"https://www.google.com/maps/dir/?api=1&destination={coords[0]},{coords[1]}"

        popup_html = f"""
        <div style="width: 280px; font-family: Arial, sans-serif;">
            <h4 style="color: {hex_color}; margin-top:0; border-bottom: 2px solid {hex_color}; padding-bottom: 5px; text-transform: uppercase;"><i class="fa fa-{fa_icon}"></i> {loai_su_co}</h4>
            <b>📍 Vị trí:</b> {dia_diem} - {dia_ban}<br>
            <b>🕒 Thời gian:</b> {thoi_gian}<br>
            <b>👤 Người báo:</b> <span style="color:#2980B9; font-weight:bold;">{nguoi_bao}</span> - 📞 {sdt_bao}<br>
            <b>👥 Ảnh hưởng:</b> {nguoi_anh_huong}<br>
            <b>🛠️ Xử lý:</b> {bien_phap}<br><br>
            <a href="{maps_url}" target="_blank" style="background-color: {hex_color}; color: white; padding: 8px 10px; text-decoration: none; border-radius: 4px; display: inline-block; text-align: center; width: 100%; font-weight:bold; box-shadow: 0px 2px 4px rgba(0,0,0,0.3); transition: 0.3s;">🗺️ Dẫn đường tới vị trí này</a>
        </div>
        """
        icon_html = f'<div class="radar-marker radar-{color_class}"><i class="fa fa-{fa_icon}"></i></div>'
        tooltip_text = folium.Tooltip(f"<b>{loai_su_co} - {dia_diem}</b><br><i style='color:red;'>👉 Bấm (Click) vào đây để xem chi tiết và Bản đồ</i>")
        folium.Marker(location=coords, popup=folium.Popup(popup_html, max_width=320), tooltip=tooltip_text, icon=DivIcon(html=icon_html, icon_size=(30, 30), icon_anchor=(15, 15))).add_to(su_co_layer)

    xa_layer.add_to(m)
    nhan_xa_layer.add_to(m)
    su_co_layer.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    if su_co_active_count > 0: 
        st.warning(f"Đang hiển thị **{su_co_active_count}** sự kiện/sự cố Xã trên bản đồ.")
    else: 
        st.success("Tất cả các sự cố Xã đã được xử lý hoặc chưa có thông tin vị trí hợp lệ.")
        
    st_folium(m, use_container_width=True, height=700, returned_objects=[])