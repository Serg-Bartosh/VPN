FROM python:3.11

COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

COPY . /app/

WORKDIR /app

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
