"""
پاکسازی حساب X (پست‌ها، ریتوییت‌ها، لایک‌ها) — نسخه Streamlit
================================================================
نصب:
    pip install streamlit selenium webdriver-manager

اجرا:
    streamlit run x_cleanup.py
"""

import time
import random
import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

try:
    from webdriver_manager.chrome import ChromeDriverManager
    HAVE_WDM = True
except ImportError:
    HAVE_WDM = False

WAIT_SECONDS = 12
PAUSE_RANGE = (1.5, 3.0)


def pause(extra=0.0):
    time.sleep(random.uniform(*PAUSE_RANGE) + extra)


def build_driver():
    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    options.add_argument("--window-size=1920,1080")

    return webdriver.Chrome(options=options)


def click_if_present(driver, selector, timeout=4):
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )
        el.click()
        return True
    except Exception:
        return False


def delete_posts_and_reposts(driver, username, log_fn, limit=None):
    driver.get(f"https://x.com/{username}")
    pause(2)
    done, empty_tries = 0, 0
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


def unlike_all_likes(driver, username, log_fn, limit=None):
    driver.get(f"https://x.com/{username}/likes")
    pause(2)
    done, empty_tries = 0, 0
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
st.caption("این کار غیرقابل بازگشت است. قبل از شروع، از Settings یک نسخه پشتیبان از داده‌هاتون بگیرید.")

if "driver" not in st.session_state:
    st.session_state.driver = None
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

username = st.text_input("نام کاربری X (بدون @)")
limit_input = st.number_input("سقف تعداد عملیات برای تست (۰ = بدون محدودیت)", min_value=0, value=0)
limit = limit_input or None

c1, c2 = st.columns(2)
with c1:
    if st.button("۱) باز کردن مرورگر برای ورود"):
        st.session_state.driver = build_driver()
        st.session_state.driver.get("https://x.com/login")
        st.info("در پنجره کروم باز شده دستی لاگین کن، بعد دکمه کنار رو بزن.")
with c2:
    if st.button("۲) لاگین شدم، ادامه بده"):
        st.session_state.logged_in = True
        st.success("آماده‌ست. حالا می‌تونی پاکسازی رو شروع کنی.")

st.divider()
log_box = st.empty()
logs = []


def log_fn(msg):
    logs.append(msg)
    log_box.code("\n".join(logs[-300:]))


ready = st.session_state.driver and st.session_state.logged_in and username

if st.button("🗑️ حذف همه پست‌ها و ریتوییت‌ها", disabled=not ready):
    count = delete_posts_and_reposts(st.session_state.driver, username, log_fn, limit)
    st.success(f"{count} پست/ریتوییت حذف شد.")

if st.button("💔 آن‌لایک کردن همه لایک‌ها", disabled=not ready):
    count = unlike_all_likes(st.session_state.driver, username, log_fn, limit)
    st.success(f"{count} لایک حذف شد.")

if not ready:
    st.warning("اول مرورگر رو باز کن، لاگین کن، و نام کاربری رو وارد کن.")
