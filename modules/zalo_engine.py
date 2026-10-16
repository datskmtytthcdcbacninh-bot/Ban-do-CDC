# File: modules/zalo_engine.py
import os
import time
import threading
import pyperclip
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

zalo_lock = threading.Lock()

def kill_zombie_chromedriver():
    try:
        if os.name == 'nt':
            os.system("taskkill /f /im chromedriver.exe >nul 2>&1")
    except: pass

def get_zalo_data_dir():
    # TRỎ TRỰC TIẾP ĐẾN ĐƯỜNG DẪN BÁC ĐÃ CẤU HÌNH TRÊN DESKTOP
    return r"C:\Users\admin\Desktop\main\Zalo_Data"

def gui_tin_nhan_qua_zalo(danh_sach_gui):
    """
    danh_sach_gui là một list các tuple: [(nguoi_nhan_1, tin_nhan_1), (nguoi_nhan_2, tin_nhan_2), ...]
    """
    if not danh_sach_gui: return []
    
    print(f"INFO: Chuẩn bị mở Zalo để gửi {len(danh_sach_gui)} tin nhắn...")
    
    if not zalo_lock.acquire(blocking=False): 
        print("WARN: Động cơ Zalo đang bận gửi tin khác. Bỏ qua lượt này.")
        return []
    
    danh_sach_thanh_cong = []
    driver = None
    
    try:
        kill_zombie_chromedriver(); time.sleep(2) 
        options = Options()
        options.add_argument(f"user-data-dir={get_zalo_data_dir()}")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_argument("--no-sandbox") 
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu") 
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.maximize_window(); driver.get("https://chat.zalo.me/")
        
        wait = WebDriverWait(driver, 60)
        try: wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="contact-search-input"] | //input[contains(@placeholder, "Tìm kiếm")]')))
        except: return [] 
        time.sleep(3.0) 
        
        for nguoi_nhan, tin_nhan in danh_sach_gui:
            retry_count = 0
            success = False
            
            while retry_count < 3 and not success:
                try:
                    search_box = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="contact-search-input"] | //input[contains(@placeholder, "Tìm kiếm")]')))
                    driver.execute_script("arguments[0].click();", search_box)
                    time.sleep(1.0)
                    
                    search_box.send_keys(Keys.CONTROL + "a", Keys.DELETE)
                    time.sleep(1.0)
                    search_box.send_keys(str(nguoi_nhan))
                    
                    time.sleep(4.0) 
                    search_box.send_keys(Keys.ARROW_DOWN, Keys.ENTER)
                    time.sleep(2.0) 
                    
                    msg_box = wait.until(EC.element_to_be_clickable((By.XPATH, '//div[@contenteditable="true"]')))
                    driver.execute_script("arguments[0].click();", msg_box)
                    time.sleep(1.0) 
                    
                    pyperclip.copy(tin_nhan)
                    time.sleep(1.0)
                    ActionChains(driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                    time.sleep(2.0) 
                    ActionChains(driver).send_keys(Keys.ENTER).perform()
                    
                    time.sleep(3.0) 
                    danh_sach_thanh_cong.append(nguoi_nhan)
                    print(f"ZALO_SUCCESS: Gửi THÀNH CÔNG cho: {nguoi_nhan}")
                    success = True
                    
                except Exception as e:
                    retry_count += 1
                    print(f"WARN: LỖI ZALO ({nguoi_nhan}) - Lần {retry_count}. Đang tự phục hồi...")
                    try:
                        driver.refresh() 
                        time.sleep(10)
                    except: pass
            time.sleep(3.0)
        return danh_sach_thanh_cong
    except Exception as e: 
        print(f"ERROR: LỖI KHỞI TẠO ZALO: {str(e)}")
        return []
    finally:
        if driver: 
            try: driver.quit()
            except: pass
        zalo_lock.release()