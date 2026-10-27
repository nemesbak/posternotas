FROM python:3.12-slim
RUN pip install --no-cache-dir flask==3.1.2 pillow==11.3.0
WORKDIR /app
COPY motor.py render.py app.py panel.html /app/
ENV PN_DATA=/data PN_FONTS=/fonts PN_ENV=/odin.env PYTHONUNBUFFERED=1
EXPOSE 8790
CMD ["python", "/app/app.py"]
