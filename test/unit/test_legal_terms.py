"""HIH-legal: страница «Условия использования» и cookie-баннер.

За чем следит этот файл: домен нигде не зашит, а текст условий один на оба сайта.
"""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "back"))

# Домены контуров не должны появляться в общих текстах и клиентском коде.
FORBIDDEN_HOSTS = (
    "hand-in-hand-kzn.ru",
    "iskusstvo-chtoby-zhit.ru",
    "hand.hand-in-hand",
)

TEMPLATE = ROOT / "legal" / "terms.ru.html"
LANDING_JS = ROOT / "landing" / "js"
FRONT_APP = ROOT / "front" / "src" / "App.tsx"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestTermsTemplate:
    def test_exists_and_non_trivial(self):
        text = read(TEMPLATE)
        assert "<article" in text
        assert len(text) > 6000

    @pytest.mark.parametrize("marker", [
        "Пользуясь этим сайтом, вы соглашаетесь",
        "Cookies",
        "Яндекс.Метрика",
        "СБП",
        "Mir Pay",
        "SberPay",
        "галерея",
        "покупка рисунков",
        "cookieConsent",
    ])
    def test_required_sections_present(self, marker):
        assert marker in read(TEMPLATE)

    def test_domain_is_a_variable_not_a_literal(self):
        text = read(TEMPLATE)
        assert "{{DOMAIN}}" in text
        for host in FORBIDDEN_HOSTS:
            assert host not in text

    def test_no_dollar_tokens_so_envsubst_safe(self):
        # nginx envsubst вырезает $var / ${var}; на странице условий нам это не нужно
        assert not re.search(r"\$\{?[A-Za-z_]", read(TEMPLATE))


class TestLandingIntegration:
    def test_terms_scripts_exist(self):
        assert (LANDING_JS / "terms.js").exists()
        assert (LANDING_JS / "cookie-consent.js").exists()

    def test_terms_js_reads_host_from_location(self):
        js = read(LANDING_JS / "terms.js")
        assert "window.location.hostname" in js
        for host in FORBIDDEN_HOSTS:
            assert host not in js

    def test_cookie_consent_contract(self):
        js = read(LANDING_JS / "cookie-consent.js")
        assert "cookieConse" in js and "nt" in js          # ключ собран из частей
        assert "Принять" in js
        assert "terms.html" in js
        for color in ("#2268b1", "#de789d", "#FBF3EA"):
            assert color in js

    def test_footer_links_to_terms(self):
        assert 'href="terms.html"' in read(ROOT / "landing" / "index.html")

    def test_page_shell_is_assembled_from_one_source(self):
        dockerfile = read(ROOT / "deploy" / "Dockerfile.landing")
        assert "legal/terms.ru.html" in dockerfile
        assert "terms.html" in dockerfile

    def test_assembled_page_has_only_the_marker(self):
        head = read(ROOT / "landing" / "terms.head.html")
        foot = read(ROOT / "landing" / "terms.foot.html")
        page = head + read(TEMPLATE) + foot
        assert page.count("{{DOMAIN}}") >= 3
        assert "<h1>Условия использования сайта</h1>" in page
        assert page.rstrip().endswith("</html>")


class TestGalleryIntegration:
    def test_app_uses_shared_template(self):
        app = read(FRONT_APP)
        assert "legal/terms.ru.html?raw" in app

    def test_app_resolves_domain_from_env_with_host_fallback(self):
        app = read(FRONT_APP)
        assert "VITE_SITE_HOST" in app
        assert "window.location.hostname" in app
        for host in FORBIDDEN_HOSTS:
            assert host not in app

    def test_app_has_terms_route_and_banner(self):
        app = read(FRONT_APP)
        assert r"/^\/terms\/?$/" in app
        assert "CookieBanner" in app
        assert 'href="/terms"' in app
        assert "cookieConsent" in app

    def test_compose_passes_site_host_to_frontend_build(self):
        compose = read(ROOT / "deploy" / "docker-compose.yml")
        assert "VITE_SITE_HOST: ${SITE_HOST:-}" in compose


class TestNoSecretsIntroduced:
    @pytest.mark.parametrize("path", [
        TEMPLATE,
        LANDING_JS / "terms.js",
        LANDING_JS / "cookie-consent.js",
        ROOT / "landing" / "terms.head.html",
        ROOT / "landing" / "terms.foot.html",
    ])
    def test_new_files_have_no_credentials(self, path):
        text = read(path).lower()
        for word in ("password", "secret", "api_key", "apikey", "token="):
            assert word not in text, f"{word} в {path.name}"
