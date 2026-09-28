FROM python:3.12-slim

WORKDIR /app

COPY back/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Опциональный корневой сертификат боевого платёжного шлюза.
# Положите файл вида *.crt в deploy/certs/ и пересоберите образ — он попадёт в
# системное хранилище. ВАЖНО: httpx по умолчанию доверяет не системному хранилищу,
# а bundle пакета certifi, поэтому вместе с сертификатом в контейнер должен
# приехать SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt (см. deploy/env/*.env)
# либо путь к сертификату в SBER_CA_BUNDLE. Подробности — back/README.md, раздел
# «Диагностика оплаты через Сбербанк».
COPY deploy/certs/ /usr/local/share/ca-certificates/sber/
RUN if ls /usr/local/share/ca-certificates/sber/*.crt >/dev/null 2>&1; then \
      apt-get update \
      && apt-get install -y --no-install-recommends ca-certificates \
      && update-ca-certificates \
      && rm -rf /var/lib/apt/lists/*; \
    else \
      echo ">> deploy/certs пуст — системный набор сертификатов не меняем"; \
    fi

COPY back ./

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
