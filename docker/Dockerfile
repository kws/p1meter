FROM python:3.13-slim

# Create unprivileged user with uid:gid 1000:1000
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g 1000 -m -s /bin/bash appuser

# Set working directory
WORKDIR /app

# Install pipx globally and use it to install poetry (as root)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir pipx && \
    pipx install poetry

# Add poetry to PATH (pipx installs to /root/.local/bin by default)
# Poetry is only needed at build time, not runtime
ENV PATH="/root/.local/bin:${PATH}"

# Copy project configuration files
COPY pyproject.toml poetry.lock* ./

# Install dependencies using poetry (as root, before switching user)
RUN poetry config virtualenvs.create false && \
    poetry install --without dev --no-interaction --no-ansi --no-root

# Copy application code
COPY p1_decoder/ ./p1_decoder/

# Change ownership of app directory to appuser
RUN chown -R appuser:appuser /app

# Switch to unprivileged user
USER appuser

# Set Python path
ENV PYTHONPATH=/app

# Default command (can be overridden in docker-compose)
CMD ["python", "-m", "p1_decoder.archive"]

