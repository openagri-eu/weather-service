FROM python:3.12 AS builder

LABEL org.opencontainers.image.source https://github.com/openagri-eu/weather-service

ARG DEBIAN_FRONTEND=noninteractive

RUN set -x && \
    apt-get update -q && \
    apt-get install -yq --no-install-recommends && \
    apt-get autoremove -yq && \
    apt-get clean -q && rm -rf /var/lib/apt/lists/* && \
    find / -name '*.py[co]' -delete

COPY requirements.txt requirements-test.txt ./

RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install -U --no-cache-dir -r requirements.txt && \
    find / -name '*.py[co]' -delete

FROM python:3.12-slim AS runner


WORKDIR /weather-service

COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# ßshared objects *.so files and fonts for building er-diagram
COPY --from=builder /usr/lib/*-linux-gnu /usr/lib/
COPY --from=builder /usr/share/fonts /usr/share/fonts

ARG USER_ID=1001
ARG GROUP_ID=1001
RUN groupadd -r openagri --gid $GROUP_ID && \
    useradd -d /home/openagri -ms /bin/bash -r -g openagri openagri --uid $USER_ID

COPY src ./src
# COPY tests ./tests
COPY run.sh ./

RUN chown -R $USER_ID:$GROUP_ID /weather-service

USER openagri

ENV USER_ID=$USER_ID \
    GROUP_ID=$GROUP_ID \
    PROJECT_DIR=/weather-service \
    PYTHONPATH=/weather-service

CMD ["./run.sh", "prod"]