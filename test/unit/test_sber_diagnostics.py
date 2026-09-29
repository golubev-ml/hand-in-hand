"""HIH-payments: диагностика «на тесте работает, на бою нет».

Проверяем разбор TLS/учётки, алиасы env, предупреждения о конфликтующих значениях
и то, что ни в один лог не попадает пароль.
"""
import os
import sys
import tempfile
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "back"))

os.environ.setdefault("APP_ENV", "local")

import settings_store                                    # noqa: E402
from payments import sber                                # noqa: E402


@pytest.fixture
def env(monkeypatch):
    """Чистая env-конфигурация шлюза + перехват логов."""
    for name in ("SBER_BASE_URL", "SBER_API_URL", "SBER_USER_NAME", "SBER_USERNAME",
                 "SBER_PASSWORD", "SBER_MERCHANT_PASSWORD", "SBER_VERIFY_SSL",
                 "SBER_CA_BUNDLE", "SSL_CERT_FILE", "SBER_TERMINAL", "SBER_KEY_ID",
                 "SBER_MERCHANT_LOGIN", "SBER_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SBER_USER_NAME", "PROD_USER")
    monkeypatch.setenv("SBER_PASSWORD", "sup3r$ecret")
    monkeypatch.setenv("SBER_TERMINAL", "2210001234")
    logs = []
    monkeypatch.setattr(sber, "log_exchange", lambda **kw: logs.append(kw))
    yield {"logs": logs, "monkeypatch": monkeypatch}
    sber._transport = None


class TestContourAndAliases:
    def test_base_url_alias_sber_api_url(self, env):
        env["monkeypatch"].setenv("SBER_API_URL", sber.PROD_BASE_URL)
        assert sber.base_url() == sber.PROD_BASE_URL
        assert sber.contour() == "prod"

    def test_canonical_name_wins_over_alias(self, env):
        mp = env["monkeypatch"]
        mp.setenv("SBER_BASE_URL", sber.TEST_BASE_URL)
        mp.setenv("SBER_API_URL", sber.PROD_BASE_URL)
        assert sber.base_url() == sber.TEST_BASE_URL

    def test_default_is_test_contour(self, env):
        assert sber.contour() == "test"

    def test_username_alias_is_reported_as_suspicious(self, env):
        mp = env["monkeypatch"]
        mp.delenv("SBER_USER_NAME")
        mp.setenv("SBER_USERNAME", "ALIAS_USER")
        value, source = settings_store.resolve(None, "sber_user_name")
        assert value == "ALIAS_USER" and "алиас" in source
        assert any("SBER_USERNAME" in w for w in settings_store.warnings(None))


class TestVerifySsl:
    def test_true_by_default(self, env):
        assert sber.verify_ssl() is True

    def test_false_only_when_asked(self, env):
        env["monkeypatch"].setenv("SBER_VERIFY_SSL", "false")
        assert sber.verify_ssl() is False

    def test_custom_bundle_path_is_used(self, env, tmp_path):
        ca = tmp_path / "nuc-root.crt"
        ca.write_text("-----BEGIN CERTIFICATE-----\n", encoding="utf-8")
        env["monkeypatch"].setenv("SBER_CA_BUNDLE", str(ca))
        assert sber.verify_ssl() == str(ca)

    def test_missing_bundle_file_falls_back_to_system(self, env):
        env["monkeypatch"].setenv("SBER_CA_BUNDLE", "/nope/nothing.crt")
        assert sber.verify_ssl() is True


class TestTlsFailure:
    def test_detects_certificate_problem_in_the_chain(self, env):
        inner = httpx.ConnectError("failed to verify certificate")
        inner.__cause__ = OSError("[SSL: CERTIFICATE_VERIFY_FAILED] unable to get local issuer certificate")
        assert sber.looks_like_tls_failure(inner)

    def test_plain_timeout_is_not_tls(self, env):
        assert not sber.looks_like_tls_failure(httpx.ConnectTimeout("timeout"))

    def test_tls_error_explains_the_root_certificate(self, env):
        exc = httpx.ConnectError("failed to verify certificate")
        exc.__cause__ = OSError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed")
        text = str(sber.tls_error("register.do", exc))
        assert "корневой сертификат" in text and "SBER_CA_BUNDLE" in text

    def test_tls_error_is_not_retried(self, env):
        calls = {"n": 0}

        def boom(_request):
            calls["n"] += 1
            err = httpx.ConnectError("failed to verify certificate")
            err.__cause__ = OSError("unable to get local issuer certificate")
            raise err

        sber._transport = httpx.MockTransport(boom)
        env["monkeypatch"].setattr(sber, "RETRIES", 3)
        with pytest.raises(sber.SberError) as info:
            sber.call("getOrderStatus.do", {"orderNumber": "1"}, http_method="GET")
        assert info.value.tls is True
        assert calls["n"] == 1                     # без трёх бессмысленных повторов

    def test_failure_is_written_to_log(self, env):
        def boom(_request):
            err = httpx.ConnectError("failed to verify certificate")
            err.__cause__ = OSError("unable to get local issuer certificate")
            raise err

        sber._transport = httpx.MockTransport(boom)
        with pytest.raises(sber.SberError):
            sber.call("register.do", {"orderNumber": "7"})
        assert len(env["logs"]) == 1
        assert "СБОЙ" in env["logs"][0]["text"]


class TestLogsNeverLeakSecrets:
    def _ok_transport(self):
        sber._transport = httpx.MockTransport(
            lambda request: httpx.Response(200, json={"errorCode": "0", "orderId": "42"}))

    def test_context_has_identity_but_not_password(self, env):
        self._ok_transport()
        sber.call("register.do", {"orderNumber": "7"})
        entry = env["logs"][0]
        blob = " ".join(str(v) for v in entry.values())
        assert "PROD_USER" in blob
        assert "2210001234" in blob                 # terminal тоже виден
        assert "register.do" in blob
        assert "sup3r$ecret" not in blob
        assert '"password": "***"' in blob          # значение замаскировано в самом теле

    def test_describe_line_is_safe(self, env):
        line = sber.describe(None)
        assert "userName=PROD_USER" in line and "terminal=2210001234" in line
        assert "sup3r$ecret" not in line


class TestDiagnose:
    def _with(self, payload):
        sber._transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))

    def test_no_credentials(self, env):
        env["monkeypatch"].delenv("SBER_USER_NAME")
        env["monkeypatch"].delenv("SBER_PASSWORD")
        report = sber.diagnose(None)
        assert report["kind"] == "no_credentials" and report["ok"] is False

    def test_wrong_password_is_reported_as_auth(self, env):
        self._with({"errorCode": "215", "errorMessage": "Неверное имя пользователя или пароль"})
        report = sber.diagnose(None)
        assert report["kind"] == "auth" and report["ok"] is False
        assert "215" in report["detail"]

    def test_order_not_found_means_credentials_are_fine(self, env):
        self._with({"errorCode": "105", "errorMessage": "Заказ с таким номером не найден"})
        report = sber.diagnose(None)
        assert report["ok"] is True and report["kind"] == "answered"

    def test_tls_problem_is_separated_from_auth(self, env):
        def boom(_request):
            err = httpx.ConnectError("failed to verify certificate")
            err.__cause__ = OSError("unable to get local issuer certificate")
            raise err

        sber._transport = httpx.MockTransport(boom)
        report = sber.diagnose(None)
        assert report["kind"] == "tls" and report["ok"] is False

    def test_report_carries_configuration_warnings(self, env):
        env["monkeypatch"].setenv("SBER_PASSWORD", "p@ss$word")
        self._with({"errorCode": "0"})
        report = sber.diagnose(None)
        assert any("$" in w for w in report["warnings"])


class TestSettingsStoreWarnings:
    def test_db_and_env_disagreement_is_flagged(self, env, tmp_path):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        import models
        engine = create_engine(f"sqlite:///{tmp_path/'t.db'}")
        models.Base.metadata.create_all(engine)
        db = sessionmaker(bind=engine)()
        settings_store.set_value(db, "sber_user_name", "TEST_USER_FROM_DB")
        notes = settings_store.warnings(db)
        assert any("РАЗНЫЕ значения" in n for n in notes)
        # и именно значение из БД уезжает в шлюз
        assert settings_store.get_value(db, "sber_user_name") == "TEST_USER_FROM_DB"
        assert "БД (админка)" in settings_store.resolve(db, "sber_user_name")[1]
        db.close()

    def test_dollar_in_secret_is_flagged(self, env):
        assert any("$" in w for w in settings_store.warnings(None))


class TestAdminDiagnosticsUi:
    @pytest.fixture
    def client(self, monkeypatch, tmp_path):
        import database
        import main
        from auth import hash_password
        from models import Manager
        from fastapi.testclient import TestClient

        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        engine = database.create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
        TestSession = database.sessionmaker(autocommit=False, autoflush=False, bind=engine)
        database.Base.metadata.create_all(engine)
        original = (database.engine, database.SessionLocal, main.SessionLocal)
        database.engine, database.SessionLocal, main.SessionLocal = engine, TestSession, TestSession

        boot = TestSession()
        boot.add(Manager(login="root", password_hash=hash_password("pw-12345"), status="active"))
        boot.commit()
        boot.close()
        monkeypatch.setenv("BASE_URL", "http://testserver")
        main.RATE_LIMITS.clear()
        with TestClient(main.app) as c:
            r = c.post("/admin/login", data={"login": "root", "password": "pw-12345"},
                       follow_redirects=False)
            assert r.status_code == 302, f"логин не прошёл: {r.status_code}"
            yield c, TestSession
        main.RATE_LIMITS.clear()
        database.engine, database.SessionLocal, main.SessionLocal = original
        engine.dispose()
        os.unlink(path)

    def test_settings_page_shows_contour_and_sources(self, env, client, monkeypatch):
        c, _ = client
        monkeypatch.setenv("SBER_BASE_URL", sber.PROD_BASE_URL)
        html = c.get("/admin/settings").text
        assert "Контур шлюза" in html and "PROD" in html
        assert "работает значение" in html
        assert "Проверить доступ к шлюзу" in html
        assert "sup3r$ecret" not in html

    def test_diagnose_button_reports_without_password(self, env, client):
        c, Session = client
        sber._transport = httpx.MockTransport(
            lambda request: httpx.Response(200, json={"errorCode": "215",
                                                      "errorMessage": "Неверное имя пользователя или пароль"}))
        r = c.post("/admin/settings/diagnose", follow_redirects=False)
        assert r.status_code == 302
        assert "auth" in r.headers["location"]
        page = c.get(r.headers["location"]).text
        assert "Неверное имя пользователя или пароль" in page
        assert "sup3r$ecret" not in page

        db = Session()
        from models import Log
        row = db.query(Log).filter(Log.url == "/admin/settings/diagnose").order_by(Log.id.desc()).first()
        assert row is not None and "auth" in row.text
        blob = f"{row.request} {row.response}"
        assert "sup3r$ecret" not in blob and "PROD_USER" in blob
        db.close()
        sber._transport = None
