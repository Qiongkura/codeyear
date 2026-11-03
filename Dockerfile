FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir .

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "codeyear serve --host 0.0.0.0 --port ${PORT:-8000} --max-commits ${MAX_COMMITS:-200}"]
