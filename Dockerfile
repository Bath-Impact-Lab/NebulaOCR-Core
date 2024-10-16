# Use the kkwok/docker-python3-opencv-poppler:tesseract-v1 base image
FROM kkwok/docker-python3-opencv-poppler:tesseract-v1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt first to leverage Docker cache
COPY requirements.txt .

# Upgrade pip to the latest version
RUN pip install --upgrade pip

# Install Python dependencies with pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files
COPY . .

EXPOSE 8000

# Set the PORT environment variable if not already set
ENV PORT 8000

# Command to run the OCR script (adjust as needed)
CMD ["python3", "main.py"]