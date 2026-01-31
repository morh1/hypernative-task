FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . /app

CMD ["python", "-c", "print('Use: docker run ... python part1.py / part2.py')"]
