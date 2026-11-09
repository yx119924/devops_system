FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    PIP_NO_CACHE_DIR=1
RUN sed -i 's@deb.debian.org@mirrors.aliyun.com@g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends build-essential default-libmysqlclient-dev pkg-config curl \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /backend
COPY backend/requirements.txt .
# ★ 与 django/Dockerfile 保持一致：清华源缺 dvadmin3-celery，必须给官方源兜底。
RUN pip install \
    -i https://pypi.tuna.tsinghua.edu.cn/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    --retries 5 --timeout 60 \
    -r requirements.txt
ENV C_FORCE_ROOT=1
CMD ["celery", "-A", "application", "worker", "-B", "--loglevel=info"]
