FROM alpine:latest 
RUN apk add --no-cache python3 py3-pip gcompat
WORKDIR /app
# COPY requirements.txt .
# RUN pip install -r requirements.txt
COPY . .
CMD ["python3", "citizen.py"]