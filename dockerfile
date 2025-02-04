FROM python:3.10-slim-buster
WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --upgrade pip  # Update pip first
RUN pip install --upgrade pip setuptools wheel
RUN pip install psycopg2-binary
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
