"""
پاکسازی حساب X (پست‌ها، ریتوییت‌ها، لایک‌ها) — نسخه Streamlit (بدون ورود دستی)
===============================================================================
نصب:
    pip install streamlit selenium webdriver-manager

اجرا:
    streamlit run x_cleanup.py
"""
import json
import time
import random

import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

try:
    from webdriver_manager.chrome import ChromeDriverManager
    HAVE_WDM = True
except ImportError:
    HAVE_WDM = False

# ----------------------------- تنظیمات -----------------------------
WAIT_SECONDS = 12
PAUSE_RANGE = (1.5, 3.0)


def pause(extra: float = 0.0) -> None:
    """مکث تصادفی برای شبیه‌سازی رفتار انسانی"""
    time.sleep(random.uniform(*PAUSE_RANGE) + extra)


def build_driver() -> webdriver.Chrome:
    """ساخت و پیکربندی درایور کروم (حالت بدون رابط کاربری)"""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    if HAVE_WDM:
        service = webdriver.ChromeService(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)
    else:
        return webdriver.Chrome(options=options)


def ensure_driver_with_cookies() -> webdriver.Chrome | None:
    """
    اگر درایور هنوز ساخته نشده، آن را می‌سازد و کوکی‌های بارگذاری‌شده را روی آن اعمال می‌کند.
    درایور را در session_state ذخیره می‌کند.
    """
    if "driver" in st.session_state and st.session_state.driver is not None:
        return st.session_state.driver

    cookie_file = st.session_state.get("cookie_file")
    if cookie_file is None:
        st.error("لطفاً ابتدا فایل کوکی X را بارگذاری کنید.")
        return None

    driver = build_driver()
    driver.get("https://x.com")
    cookies = json.loads(cookie_file.getvalue())
    for cookie in cookies:
        cookie.pop("sameSite", None)  # Selenium این کلید را نمی‌پذیرد
        try:
            driver.add_cookie(cookie)
        except Exception as e:
            st.warning(f"خطا در افزودن کوکی: {e}")
    driver.refresh()
    st.session_state.driver = driver
    return driver


def click_if_present(driver, selector: str, timeout: int = 4) -> bool:
    """اگر عنصر قابل کلیک وجود داشت روی آن کلیک کند"""
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )
        el.click()
        return True
    except Exception:
        return False


def delete_posts_and_reposts(driver, username: str, log_fn, limit: int | None = None) -> int:
    """حذف تمام پست‌ها و بازنشرها (ریتوییت‌ها)"""
    driver.get(f"https://x.com/{username}")
    pause(2)
    done = 0
    empty_tries = 0

    while not (limit and done >= limit):
        try:
            caret = WebDriverWait(driver, WAIT_SECONDS).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="caret"]'))
            )
            caret.click()
            pause()
            option = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    '//span[text()="Delete" or text()="Undo repost" or text()="Undo Repost"]',
                ))
            )
            label = option.text
            option.click()
            pause()
            if label.lower().startswith("delete"):
                click_if_present(driver, '[data-testid="confirmationSheetConfirm"]')
            done += 1
            empty_tries = 0
            log_fn(f"[{done}] {label} ✅")
            pause(1)
            driver.refresh()
            pause(2)
        except (TimeoutException, NoSuchElementException):
            empty_tries += 1
            if empty_tries >= 3:
                break
            driver.refresh()
            pause(3)
    return done


def unlike_all_likes(driver, username: str, log_fn, limit: int | None = None) -> int:
    """آن‌لایک کردن تمام لایک‌ها"""
    driver.get(f"https://x.com/{username}/likes")
    pause(2)
    done = 0
    empty_tries = 0

    while not (limit and done >= limit):
        try:
            heart = WebDriverWait(driver, WAIT_SECONDS).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="unlike"]'))
            )
            heart.click()
            done += 1
            empty_tries = 0
            log_fn(f"[{done}] لایک حذف شد ❤️‍🩹")
            pause()
        except (TimeoutException, NoSuchElementException):
            empty_tries += 1
            driver.execute_script("window.scrollBy(0, 400);")
            pause(2)
            if empty_tries >= 3:
                break
    return done


# ----------------------------- رابط کاربری -----------------------------
st.set_page_config(page_title="پاکسازی حساب X", page_icon="🧹")
st.title("🧹 پاکسازی پست‌ها، ریتوییت‌ها و لایک‌های X")
st.caption(
    "این کار غیرقابل بازگشت است. قبل از شروع، از Settings یک نسخه پشتیبان از داده‌هاتون بگیرید."
)

# ورودی‌ها
cookie_file = st.file_uploader(
    "📁 فایل کوکی X را بارگذاری کنید (خروجی افزونه‌های مدیریت کوکی)",
    type=["json"],
    key="cookie_file"
)
username = st.text_input("👤 نام کاربری X (بدون @)")
limit_input = st.number_input(
    "🔢 سقف تعداد عملیات برای تست (۰ = بدون محدودیت)",
    min_value=0,
    value=0
)
limit = limit_input if limit_input > 0 else None

# نمایش لاگ‌ها
log_box = st.empty()
logs = []


def log_fn(msg: str) -> None:
    logs.append(msg)
    log_box.code("\n".join(logs[-300:]))


# دکمه‌های عملیات
col1, col2 = st.columns(2)
with col1:
    if st.button("🗑️ حذف همه پست‌ها و ریتوییت‌ها", use_container_width=True):
        if not cookie_file:
            st.error("لطفاً فایل کوکی را بارگذاری کنید.")
        elif not username:
            st.error("نام کاربری را وارد کنید.")
        else:
            driver = ensure_driver_with_cookies()
            if driver:
                with st.spinner("در حال حذف پست‌ها و ریتوییت‌ها..."):
                    count = delete_posts_and_reposts(driver, username, log_fn, limit)
                    driver.save_screenshot("debug.png")
                    print(driver.page_source[:5000])
                    st.image("debug.png")
                st.success(f"{count} پست/ریتوییت حذف شد.")

with col2:
    if st.button("💔 آن‌لایک کردن همه لایک‌ها", use_container_width=True):
        if not cookie_file:
            st.error("لطفاً فایل کوکی را بارگذاری کنید.")
        elif not username:
            st.error("نام کاربری را وارد کنید.")
        else:
            driver = ensure_driver_with_cookies()
            if driver:
                with st.spinner("در حال حذف لایک‌ها..."):
                    count = unlike_all_likes(driver, username, log_fn, limit)
                st.success(f"{count} لایک حذف شد.")
