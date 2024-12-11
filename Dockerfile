# Use official Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Create and activate virtual environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

# Create virtual environment
RUN python -m venv /opt/venv

# Copy only the requirements file first
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Gunicorn
RUN pip install --no-cache-dir gunicorn

# Copy the rest of the application files
COPY . .

# Expose the port
EXPOSE 5000

# Set production mode
ENV FLASK_ENV=production

# Run with Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "120", "app:app"]