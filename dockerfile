# Base image for Python
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    npm \
    && apt-get clean

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files into the container
COPY . /app/

# Install Tailwind dependencies via npm
WORKDIR /app/surakshak/theme/static_src
RUN npm install

# Run the Tailwind build step
WORKDIR /app
RUN python manage.py tailwind build

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose the development server port
EXPOSE 8000

# Command to start both Django and Tailwind's watch process
CMD ["sh", "-c", "python manage.py tailwind start & python manage.py runserver 0.0.0.0:8000"]

# Use the official Python image as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1  # Prevents Python from writing .pyc files
ENV PYTHONUNBUFFERED 1        # Ensures logs are output immediately

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . /app/

# Expose the port the app runs on
EXPOSE 8000

# Run the application
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
