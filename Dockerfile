FROM docker.m.daocloud.io/library/python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com --no-cache-dir -r requirements.txt

COPY . .

# Expose the port
EXPOSE 8900

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8901"]
