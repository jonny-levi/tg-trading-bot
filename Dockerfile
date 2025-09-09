# Use a slim Python image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && pip install -r requirements.txt

# Set environment variable for Flask (לא חובה כאן אבל לא מזיק)
ENV PORT=8080

# Expose port for Flask or other HTTP server
EXPOSE 8080

# Run the main script
CMD ["python", "main.py"]
