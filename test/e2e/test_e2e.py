import os
from playwright.sync_api import expect

BASE = os.getenv("BASE_URL", "https://hand-in-hand-kzn.ru")


def test_gallery_and_admin(page):
    page.goto(BASE)
    expect(page.get_by_text("Краски детства").first).to_be_visible(timeout=15000)
    page.goto(f"{BASE}/admin/login")
    page.fill('input[name="login"]', os.environ["ADMIN_LOGIN"])
    page.fill('input[name="password"]', os.environ["ADMIN_PASSWORD"])
    page.click("button")
    expect(page.get_by_text("Заказы").first).to_be_visible(timeout=15000)
