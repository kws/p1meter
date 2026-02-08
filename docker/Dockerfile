FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install pipx globally and use it to install poetry
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir pipx && \
    pipx install poetry

# Add pipx bin to PATH (poetry is installed via pipx)
ENV PATH="/root/.local/bin:${PATH}"

# Copy project configuration files
COPY pyproject.toml poetry.lock* ./

# Install dependencies using poetry
RUN poetry config virtualenvs.create false && \
    poetry install --without dev --no-interaction --no-ansi --no-root

# Copy application code
COPY p1_decoder/ ./p1_decoder/

# Set Python path
ENV PYTHONPATH=/app

# Default command (can be overridden in docker-compose)
CMD ["python", "-m", "p1_decoder.archive"]

