"""Temporary local helper for README screenshots."""

import sqlite3
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select


BASE = "http://127.0.0.1:5000"
USERNAME = "demo_reader"
PASSWORD = "capture-only-password"

options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--hide-scrollbars")
options.add_argument("--force-device-scale-factor=1")
options.add_argument("--window-size=1440,1000")
driver = webdriver.Chrome(options=options)

try:
    driver.get(BASE)
    time.sleep(2)
    driver.save_screenshot("photos/landing.png")

    driver.get(f"{BASE}/login")
    time.sleep(1)
    driver.save_screenshot("photos/sign-in.png")

    driver.get(f"{BASE}/register")
    driver.find_element(By.ID, "username").send_keys(USERNAME)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.ID, "registerForm").submit()
    time.sleep(1)

    driver.find_element(By.ID, "username").send_keys(USERNAME)
    driver.find_element(By.ID, "password").send_keys(PASSWORD)
    driver.find_element(By.ID, "loginForm").submit()
    time.sleep(1)

    driver.find_element(By.XPATH, "//button[contains(., 'Set today')]").click()
    driver.find_element(By.ID, "targetMinutes").send_keys("120")
    driver.find_element(By.ID, "goalSubject").send_keys("Linear Algebra")
    driver.find_element(By.XPATH, "//button[contains(., 'Save today')]").click()
    time.sleep(1)

    for subject, duration, mood, productivity, notes in (
        ("Linear Algebra", "45", "good", "high", "Eigenvectors and diagonalisation"),
        ("Physics", "35", "excellent", "very_high", "Electric fields practice"),
        ("Algorithms", "25", "good", "high", "Dynamic programming review"),
    ):
        driver.get(f"{BASE}/log_session")
        driver.find_element(By.ID, "subject").send_keys(subject)
        driver.find_element(By.ID, "duration").send_keys(duration)
        Select(driver.find_element(By.ID, "mood")).select_by_value(mood)
        Select(driver.find_element(By.ID, "productivity")).select_by_value(productivity)
        driver.find_element(By.ID, "notes").send_keys(notes)
        driver.find_element(By.ID, "logSessionForm").submit()
        time.sleep(.5)

    driver.get(f"{BASE}/dashboard")
    time.sleep(2)
    driver.save_screenshot("photos/today.png")

    driver.get(f"{BASE}/pomodoro")
    time.sleep(1)
    driver.find_element(By.CLASS_NAME, "pomo-preset-card").click()
    time.sleep(2)
    driver.save_screenshot("photos/focus.png")
finally:
    driver.quit()
    with sqlite3.connect("study_tracker.db") as connection:
        connection.execute("DELETE FROM users WHERE username = ?", (USERNAME,))
        connection.commit()
