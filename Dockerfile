# Use the official Python image from the Docker Hub
FROM python:3.12.7-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt first to leverage Docker cache
COPY requirements.txt .

# Install poppler-utils and other dependencies
RUN apt-get update && \
    apt-get install -y poppler-utils && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files
COPY . .

# Command to run the OCR script (adjust as needed)
CMD ["python", "main.py"]