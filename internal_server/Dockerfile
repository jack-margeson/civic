FROM python:3.13.1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt 
COPY . .
ENV TERM xterm
CMD ["python3", "civic_server.py"]