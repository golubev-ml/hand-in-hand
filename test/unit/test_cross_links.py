"""Плашка «Лендинг ↔ Галерея» и карусель рисунков.

Слежим за двумя вещами: домен нигде не зашит, и карусель не остаётся пустой,
когда API галереи недоступен.
"""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "back"))

FORBIDDEN_HOSTS = ("hand-in-hand-kzn.ru", "iskusstvo-chtoby-zhit.ru")

LANDING_HTML = ROOT / "landing" / "index.html"
LANDING_CSS = ROOT / "landing" / "css" / "style.css"
CAROUSEL_JS = ROOT / "landing" / "js" / "gallery-carousel.js"
CROSSLINK_JS = ROOT / "landing" / "js" / "cross-link.js"
APP_TSX = ROOT / "front" / "src" / "App.tsx"
COMPOSE = ROOT / "deploy" / "docker-compose.yml"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestLandingPlate:
    def test_plate_with_slogan_present(self):
        html = read(LANDING_HTML)
        assert 'id="xlink-gallery"' in html
        assert "Искусство, которое лечит" in html
        assert "Смотреть галерею" in html

    def test_plate_uses_env_placeholder_not_a_host(self):
        html = read(LANDING_HTML)
        assert "${SITE_URL}/#gallery" in html
        for host in FORBIDDEN_HOSTS:
            assert host not in html

    def test_plate_has_icon_and_is_in_first_screen(self):
        html = read(LANDING_HTML)
        hero = html.split('<section class="hero">')[1].split("</section>")[0]
        assert 'id="xlink-gallery"' in hero
        assert '#i-heart' in hero and '#i-arrow' in hero


class TestLandingCarousel:
    def test_markup_block_exists(self):
        html = read(LANDING_HTML)
        for marker in ('id="gallery"', 'id="gcTrack"', 'id="gcPrev"', 'id="gcNext"', 'id="gcDots"'):
            assert marker in html

    def test_script_wired(self):
        assert "js/gallery-carousel.js" in read(LANDING_HTML)

    def test_js_pulls_api_and_falls_back_to_stub(self):
        js = read(CAROUSEL_JS)
        assert "/api/pictures?status=available" in js
        assert "STUB" in js
        assert "list || STUB" in js

    def test_js_autoplay_arrows_and_reduced_motion(self):
        js = read(CAROUSEL_JS)
        assert "setInterval" in js
        assert 'addEventListener' in js and "gcPrev" in js and "gcNext" in js
        assert "prefers-reduced-motion" in js

    def test_cards_link_to_gallery(self):
        js = read(CAROUSEL_JS)
        assert "'/#gallery'" in js

    def test_no_contour_hosts_in_js(self):
        for js in (CAROUSEL_JS, CROSSLINK_JS):
            text = read(js)
            for host in FORBIDDEN_HOSTS:
                assert host not in text, f"{host} в {js.name}"

    def test_fallback_origin_keeps_the_port(self):
        # location.hostname режет порт — на нестандартном стенде ссылка и fetch
        # уходили бы на 80-й. Оба фолбэка обязаны использовать location.host.
        for js in (CAROUSEL_JS, CROSSLINK_JS):
            assert not re.search(r"location\.hostname", read(js)), js.name
        assert re.search(r"location\.host\b", read(CROSSLINK_JS))

    def test_carousel_remeasures_after_layout(self):
        # без этого точки считались по clientWidth=0 и их было на одну больше
        js = read(CAROUSEL_JS)
        assert "ResizeObserver" in js
        assert "if (!view.clientWidth)" in js

    def test_stub_is_self_contained_svg(self):
        js = read(CAROUSEL_JS)
        assert "data:image/svg+xml" in js
        assert "unsplash" not in js.lower()

    def test_styles_use_site_palette(self):
        css = read(LANDING_CSS)
        assert ".xlink" in css and ".gc-card" in css
        for token in ("var(--terra)", "var(--terra-soft)", "var(--cream)"):
            assert token in css
        assert "@media (max-width:720px)" in css          # адаптив не сломан
        assert "@media (prefers-reduced-motion:reduce)" in css


class TestGalleryPlate:
    def test_plate_rendered_in_hero(self):
        app = read(APP_TSX)
        assert "function CrossLinkPlate()" in app
        assert "<CrossLinkPlate />" in app
        hero = app.split('{/* ── Hero ── */}')[1].split("{/* ── Stats bar ── */}")[0]
        assert "<CrossLinkPlate />" in hero

    def test_landing_url_from_env_with_derived_fallback(self):
        app = read(APP_TSX)
        assert "VITE_LANDING_URL" in app
        assert "hand.${siteHost()}" in app
        for host in FORBIDDEN_HOSTS:
            assert host not in app

    def test_compose_wires_cors_and_landing_url(self):
        compose = read(COMPOSE)
        assert "VITE_LANDING_URL: https://${LANDING_DOMAIN" in compose
        assert "CORS_ORIGINS:" in compose and "${LANDING_DOMAIN" in compose

    def test_frontend_dockerfile_passes_the_arg(self):
        dockerfile = read(ROOT / "deploy" / "Dockerfile.frontend")
        assert "ARG VITE_LANDING_URL" in dockerfile
        assert "ENV VITE_LANDING_URL" in dockerfile


class TestNothingBroken:
    def test_landing_html_tags_balanced_for_sections(self):
        html = read(LANDING_HTML)
        assert html.count("<section") == html.count("</section>")

    def test_cookie_banner_and_terms_still_linked(self):
        html = read(LANDING_HTML)
        assert "js/cookie-consent.js" in html
        assert 'href="terms.html"' in html

    def test_gallery_terms_route_survives(self):
        app = read(APP_TSX)
        assert r"/^\/terms\/?$/" in app
