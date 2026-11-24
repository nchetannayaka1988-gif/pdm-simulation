FROM python:3.11-slim
WORKDIR /app
RUN pip install paho-mqtt influxdb-client numpy
COPY influx_writer.py .
CMD ["python", "influx_writer.py"]