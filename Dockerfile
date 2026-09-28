FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /code

# Belt-and-braces so console-script launches (`uv run alembic`, etc.)
# always resolve the project package regardless of sys.path[0].
ENV PYTHONPATH=/code

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

CMD ["sh", "-c", "uv run --frozen --no-sync alembic upgrade head && uv run --frozen --no-sync uvicorn app.main:app --host 0.0.0.0 --port 8000"]
