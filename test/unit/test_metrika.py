"""HIH-metrika: счётчик и цели подключаются из env, а не хардкодом.

Проверяет три вещи:
1) в исходниках нет ни одного номера счётчика — только переменные;
2) имена целей на лендинге и в галерее совпадают (иначе в кабинете Метрики
   придётся настраивать два разных списка);
3) compose принимает и короткое METRIKA_ID, и штатное YANDEX_METRIKA_ID.
"""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "back"))

# Номера счётчиков живут только в deploy/env/*.env
COUNTER_IDS = ("112291835", "112702387")

SOURCES = [
    ROOT / "front" / "index.html",
    ROOT / "front" / "src" / "App.tsx",
    ROOT / "front" / "src" / "vite-env.d.ts",
    ROOT / "landing" / "index.html",
    ROOT / "landing" / "js" / "main.js",
    ROOT / "landing" / "js" / "terms.js",
    ROOT / "landing" / "terms.head.html",
    ROOT / "landing" / "terms.foot.html",
    ROOT / "legal" / "terms.ru.html",
]

GOALS = ("donate_click", "volunteer_click", "copy_requisites", "nav_click",
         "pay_create", "pay_success")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestNoHardcodedCounter:
    @pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.name)
    def test_source_has_no_counter_number(self, path):
        text = read(path)
        for cid in COUNTER_IDS:
            assert cid not in text, f"номер счётчика {cid} зашит в {path}"

    def test_landing_uses_envsubst_variable(self):
        assert "${YANDEX_METRIKA_ID}" in read(ROOT / "landing" / "index.html")

    def test_gallery_uses_vite_env_placeholder(self):
        html = read(ROOT / "front" / "index.html")
        assert "%VITE_YANDEX_METRIKA_ID%" in html
        assert "mc.yandex.ru/metrika/tag.js" in html

    def test_gallery_publishes_id_for_goals(self):
        # reachGoal нужно знать номер счётчика — он публикуется из сниппета
        assert "window.YM_ID" in read(ROOT / "front" / "index.html")
        assert "YM_ID" in read(ROOT / "front" / "src" / "App.tsx")

    def test_invalid_or_empty_id_disables_counter(self):
        html = read(ROOT / "front" / "index.html")
        assert re.search(r"if \(!/\^\\d\+\$/.test\(id\)\) return", html)
        assert "/^\\d+$/" in read(ROOT / "landing" / "index.html")

    @pytest.mark.parametrize("profile,expected", [
        ("test.env", "112291835"),
        ("prod.env", "112702387"),
    ])
    def test_counter_ids_live_in_env_profiles(self, profile, expected):
        assert f"YANDEX_METRIKA_ID={expected}" in read(ROOT / "deploy" / "env" / profile)

    def test_compose_accepts_short_alias(self):
        compose = read(ROOT / "deploy" / "docker-compose.yml")
        assert "VITE_YANDEX_METRIKA_ID: ${METRIKA_ID:-${YANDEX_METRIKA_ID:-}}" in compose
        assert "YANDEX_METRIKA_ID: ${METRIKA_ID:-${YANDEX_METRIKA_ID:-}}" in compose


class TestGoals:
    def test_landing_fires_all_goals(self):
        js = read(ROOT / "landing" / "js" / "main.js")
        for goal in GOALS:
            assert f"'{goal}'" in js, f"на лендинге нет цели {goal}"

    def test_gallery_fires_goals_it_has_ui_for(self):
        app = read(ROOT / "front" / "src" / "App.tsx")
        for goal in ("nav_click", "donate_click", "pay_create", "pay_success"):
            assert f"'{goal}'" in app, f"в галерее нет цели {goal}"

    def test_gallery_goals_are_a_subset_of_the_landing_list(self):
        """Один и тот же набор имён настраивается в кабинете один раз."""
        app = read(ROOT / "front" / "src" / "App.tsx")
        fired = set(re.findall(r"ymGoal\('([a-z_]+)'", app))
        assert fired, "в галерее вообще нет вызовов ymGoal"
        assert fired <= set(GOALS), f"неизвестные цели: {fired - set(GOALS)}"

    def test_goal_calls_are_guarded(self):
        app = read(ROOT / "front" / "src" / "App.tsx")
        helper = app.split("function ymGoal(")[1].split("\n}")[0]
        assert "try" in helper and "typeof window.ym === 'function'" in helper

    def test_nav_click_carries_the_section(self):
        app = read(ROOT / "front" / "src" / "App.tsx")
        assert "section: '#' + id" in app
