FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y wget tar
RUN wget https://github.com/fastfetch-cli/fastfetch/releases/download/2.42.0/fastfetch-linux-amd64.deb && dpkg -i fastfetch-linux-amd64.deb

COPY . .
RUN python -m pip install -r requirements.txt

WORKDIR /app
COPY . /app
RUN wget https://github.com/homeport/termshot/releases/download/v0.5.0/termshot_0.5.0_linux_amd64.tar.gz && tar xzf termshot_0.5.0_linux_amd64.tar.gz

RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

CMD ["python", "main.py"]