FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir pydantic fastapi uvicorn
COPY validate_invoice.py server.py /app/
EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
