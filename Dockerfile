# This docker file defines the environment for the AIS Scanner project.

ARG PYTHON_VERSION=3.13.7
# Use a simple base image with Python installed. The slim variant is small and sufficient for the application.
FROM python:${PYTHON_VERSION}-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container to /app.
WORKDIR /app

# Create a non-privileged user that the app will run under.
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid "${UID}" \
    appuser

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt

# Switch to the non-privileged user to run the application.
USER appuser

# Copy the source code into the container. 
COPY . .

# Run the AIS scanner.
ENTRYPOINT ["python", "main.py"]
