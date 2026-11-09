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
# ★ --extra-index-url 是必需项，不是保险：
#   清华源缺 dvadmin3-celery，只有主源时 pip 会直接失败、整个镜像构建卡死（踩过两次）。
#   主源仍用清华（国内快），缺的包自动回落官方源。
RUN pip install \
    -i https://pypi.tuna.tsinghua.edu.cn/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    --retries 5 --timeout 60 \
    -r requirements.txt
CMD ["sh", "docker_start.sh"]
