# Use official Python 3.11 slim base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy and install dependencies first (layer caching optimization)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the source code
COPY . .

# Expose Cloud Run's default port
EXPOSE 8080

# Run the Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
