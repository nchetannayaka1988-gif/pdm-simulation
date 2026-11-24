FROM python:3.11-slim
WORKDIR /app
RUN pip install asyncua paho-mqtt pandas numpy
COPY opcua_server.py .
CMD ["python", "opcua_server.py"]