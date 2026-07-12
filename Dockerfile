FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN useradd --create-home --shell /usr/sbin/nologin appuser

COPY dependences.txt .
RUN python -m pip install --upgrade pip \
    && python -m pip install -r dependences.txt

COPY . .
RUN chmod +x scripts/render_web.sh scripts/render_worker.sh scripts/render_beat.sh \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 5000 10000

CMD ["./scripts/render_web.sh"]
