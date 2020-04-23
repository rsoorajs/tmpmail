FROM python:3.8-slim AS builder
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/venv/bin:$PATH"
COPY . .
RUN python3 -m venv /venv \
	&& pip install --no-cache-dir "poetry>=1.0.3,<2.0" \
	&& poetry export --format=requirements.txt >> requirements.txt \
	&& poetry build --no-interaction --no-ansi \
	&& pip uninstall --yes poetry \
	&& pip install --no-cache-dir -r requirements.txt \
	&& pip install --no-cache-dir dist/tmpmail*.whl

FROM python:3.8-slim AS app
WORKDIR /app
ENV PATH="/venv/bin:$PATH"
COPY --from=builder /venv /venv
CMD ["python3", "-m", "tmpmail"]

EXPOSE 8080
EXPOSE 2525
