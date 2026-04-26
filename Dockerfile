# Use official Python slim image
FROM python:3.10-slim

# Install system dependencies — pdflatex + xelatex + tesseract + Unicode fonts
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    texlive-base \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-xetex \
    texlive-lang-other \
    fonts-freefont-ttf \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Expose port
EXPOSE 10000

# Start gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
