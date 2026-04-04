FROM python:3.10

# Set the working directory
WORKDIR /app

# 1. Copy the requirements file first (for faster caching)
COPY requirements.txt .

# 2. Install EVERYTHING in the requirements file
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy the rest of your code
COPY . .

# 4. Start the server
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]