# # Use an official Python runtime as a parent image
# FROM python:3.10-slim

# # Set the working directory in the container
# WORKDIR /usr/src/app

# # Copy the requirements file
# COPY requirements.txt ./

# # Install PyTorch (CPU-only) with a long timeout
# RUN pip install --timeout=900 torch --index-url https://download.pytorch.org/whl/cpu

# # Then, install the rest of your requirements from your file, also with a long timeout
# RUN pip install --timeout=900 --no-cache-dir -r requirements.txt

# # Copy the rest of the application code
# COPY . .

# # Define the command to run your worker in unbuffered mode
# CMD [ "python", "-u", "api.py" ]



# ================= Base Image =================
FROM python:3.10-slim

# ================= Environment =================
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV LANGCHAIN_TRACING_V2=false

# ================= System Dependencies =================
RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ================= Work Directory =================
WORKDIR /usr/src/app

# ================= Python Dependencies =================
COPY requirements.txt .

# Upgrade pip (important for resolver stability)
RUN pip install --upgrade pip

# Install PyTorch (CPU only)
RUN pip install --timeout=900 --no-cache-dir \
    torch --index-url https://download.pytorch.org/whl/cpu

# Install remaining Python dependencies
RUN pip install --timeout=900 --no-cache-dir -r requirements.txt

# ================= Application Code =================
COPY . .

# ================= Run Application =================
CMD ["python", "-u", "api.py"]
