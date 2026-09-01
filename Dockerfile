FROM mcr.microsoft.com/devcontainers/base:ubuntu@sha256:c645a61e31f3efbacde72079d7807c811c9093a52656b09b836c60612e3c427a

ARG SOURCE_REVISION
ARG EPROVER_COMMIT=8fb92857b9acb8a00c4038958ec0412a0c06ded4

LABEL org.opencontainers.image.title="VNU-HUS IntroAI Classroom50 environment"
LABEL org.opencontainers.image.source="https://github.com/hoanganhduc/VNU-HUS-IntroAI-Exercises"
LABEL org.opencontainers.image.revision="${SOURCE_REVISION}"
LABEL org.opencontainers.image.description="Development environment for VNU-HUS IntroAI Classroom50 assignments"

RUN apt-get update && \
    apt-get install -y --no-install-recommends swi-prolog gprolog && \
    rm -rf /var/lib/apt/lists/*

RUN git init /usr/src/eprover && \
    git -C /usr/src/eprover remote add origin https://github.com/eprover/eprover.git && \
    git -C /usr/src/eprover fetch --depth 1 origin "${EPROVER_COMMIT}" && \
    git -C /usr/src/eprover checkout --detach FETCH_HEAD && \
    cd /usr/src/eprover && \
    ./configure --bindir=/usr/bin && \
    make && \
    make install

RUN mkdir -p /usr/local/share/vnu-hus-introai && \
    dpkg-query -W -f='${binary:Package}\t${Version}\n' | sort \
      > /usr/local/share/vnu-hus-introai/installed-packages.tsv
