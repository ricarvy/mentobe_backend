FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 复制海外环境变量为本地配置 (因为 config.py 指定了 .env.local)
COPY .env.oversea.prod .env.local

# Expose the port
EXPOSE 8901

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8901"]
