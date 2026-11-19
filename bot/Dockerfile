# Отдельный сборочный образ
FROM python:3.12-slim-bullseye AS compile-image

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt


# Итоговый образ, в котором будет работать бот
FROM python:3.12-slim-bullseye

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    locales \
    fonts-dejavu-core \
    && sed -i '/uk_UA.UTF-8/s/^# //g' /etc/locale.gen \
    && locale-gen \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=uk_UA.UTF-8
ENV PATH="/opt/venv/bin:$PATH"

COPY --from=compile-image /opt/venv /opt/venv

WORKDIR /app
COPY . /app/bot

CMD ["python", "bot/__main__.py"]