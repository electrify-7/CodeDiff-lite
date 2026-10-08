# Ubuntu jammy-20260924.1, linux/amd64 manifest (the experimental host).
FROM ubuntu@sha256:08ea48a03a3e78ebc7cd526e6a275053223aadd88bfc09cc49b06d5281525fde

# Minimal Ubuntu has no TLS roots. Bootstrap a checksum-verified certificate
# package before accessing the HTTPS-only snapshot service.
ADD --checksum=sha256:6e8cdcc8c86103acd4fc14649eac62ff2037108389074a7b167567af33c32245 \
    https://archive.ubuntu.com/ubuntu/pool/main/c/ca-certificates/ca-certificates_20260601~22.04.1_all.deb /tmp/ca.deb
RUN dpkg-deb -x /tmp/ca.deb /tmp/ca \
    && mkdir -p /etc/ssl/certs \
    && cat /tmp/ca/usr/share/ca-certificates/mozilla/*.crt > /etc/ssl/certs/ca-certificates.crt \
    && rm -rf /tmp/ca /tmp/ca.deb

ARG DEBIAN_FRONTEND=noninteractive
# A fixed archive also freezes transitive dependency resolution.
ARG UBUNTU_SNAPSHOT=20261001T000000Z
RUN printf 'deb [check-valid-until=no] https://snapshot.ubuntu.com/ubuntu/%s jammy main universe\ndeb [check-valid-until=no] https://snapshot.ubuntu.com/ubuntu/%s jammy-updates main universe\ndeb [check-valid-until=no] https://snapshot.ubuntu.com/ubuntu/%s jammy-security main universe\n' \
      "$UBUNTU_SNAPSHOT" "$UBUNTU_SNAPSHOT" "$UBUNTU_SNAPSHOT" > /etc/apt/sources.list \
    && apt-get update -o APT::Update::Error-Mode=any \
    && apt-get install -y --no-install-recommends \
      gcc-11=11.4.0-1ubuntu1~22.04.3 \
      clang-14=1:14.0.0-1ubuntu1.1 \
      llvm-14=1:14.0.0-1ubuntu1.1 \
      libclang-common-14-dev=1:14.0.0-1ubuntu1.1 \
      python3=3.10.6-1~22.04.1 \
      python3.10=3.10.12-1~22.04.18 \
      ca-certificates=20260601~22.04.1 \
      libc6-dev \
    && mkdir -p /opt/covdiff \
    && dpkg-query -W -f='${Package}\t${Version}\n' > /opt/covdiff/packages.tsv \
    && rm -rf /var/lib/apt/lists/*

ENV COVDIFF_GCC=gcc-11 COVDIFF_GCOV=gcov-11 \
    COVDIFF_CLANG=clang-14 COVDIFF_LLVM_COV=llvm-cov-14 \
    COVDIFF_LLVM_PROFDATA=llvm-profdata-14 \
    COVDIFF_EXECUTION=container PYTHONPATH=/work/src \
    PYTHONDONTWRITEBYTECODE=1 LC_ALL=C TZ=UTC
WORKDIR /work
CMD ["python3", "-m", "covdiff_lite", "doctor"]
