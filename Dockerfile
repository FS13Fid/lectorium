# © 2026 Синакаев Фидель, Мучкаев Марк, Бутров Трофим, Борисов Никита, Попов Роман. Все права защищены. Исходный код: просмотр жюри для оценки; иное использование — по письменному разрешению правообладателей. Полные условия: LICENSE.
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /srv/lectorium
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app ./app
RUN mkdir -p /srv/lectorium/data /srv/lectorium/uploads
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
