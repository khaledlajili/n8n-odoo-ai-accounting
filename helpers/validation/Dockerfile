FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir pydantic fastapi uvicorn psycopg2-binary
COPY validate_invoice.py match_invoice.py odoo_proxy.py reviews.py server.py /app/
EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
