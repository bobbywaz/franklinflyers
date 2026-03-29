FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user 'pwuser' for running Playwright and the app
RUN groupadd -r pwuser && useradd -r -m -d /home/pwuser -g pwuser -G audio,video pwuser \
    && mkdir -p /home/pwuser/Downloads \
    && chown -R pwuser:pwuser /home/pwuser

# Switch to the non-root user to install Playwright browsers in their home directory
USER pwuser

# Install browsers for Playwright as the non-root user (benefits from caching)
RUN playwright install chromium

# Switch back to root temporarily to copy the app and change ownership
USER root

COPY --chown=pwuser:pwuser . .

# Switch back to the non-root user for running the application
USER pwuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]