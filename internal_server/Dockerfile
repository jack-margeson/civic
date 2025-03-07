FROM alpine:latest 
RUN apk add --no-cache python3 py3-pip
WORKDIR /app
COPY . /app
# RUN pip install -r requirements.txt
CMD ["python3", "civic_server.py"]