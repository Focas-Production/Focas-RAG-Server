# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the requirements file
COPY requirements.txt ./

# Install PyTorch (CPU-only) with a long timeout
RUN pip install --timeout=900 torch --index-url https://download.pytorch.org/whl/cpu

# Then, install the rest of your requirements from your file, also with a long timeout
RUN pip install --timeout=900 --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Define the command to run your worker in unbuffered mode
CMD [ "python", "-u", "main.py" ]