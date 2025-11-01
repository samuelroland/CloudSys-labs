# Syntax=docker/dockerfile:1

# Stage 1: Build Stage
FROM python:3.11-slim-bullseye AS builder

# Set working directory
WORKDIR /app

# Install required packages
COPY requirements.txt requirements.txt
RUN python -m venv venv
RUN . venv/bin/activate && pip install --no-cache-dir -r requirements.txt
# The cretion of a virtual environment facilitates the passage of dependencies between the stages. 
# It ensures minimal dependencies are copied to the runtime stage.
# It also ensures that the runtime stage is isolated from the build stage. Making the image smaller.

# Copy your application code
COPY . .

# Stage 2: Runtime Stage
FROM python:3.11-slim-bullseye

# Set working directory
WORKDIR /app

# Copy the application and virtual environment from builder image
COPY --from=builder /app /app

# Activate virtual environment and set PATH
ENV PATH="/app/venv/bin:$PATH"

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Set the command to keep the container running and idle
CMD ["python", "main.py"] 
