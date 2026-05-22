# ADR-0005-pending gateway stub. NOT FOR DEPLOYMENT.
# See .agents/gateway/README.md.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp_server.py ./

ENV SWARMS_GATEWAY_STUB_ACK=1
EXPOSE 8080

CMD ["uvicorn", "mcp_server:app", "--host", "0.0.0.0", "--port", "8080"]
