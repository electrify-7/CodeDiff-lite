# Ubuntu jammy-20260924.1, linux/amd64 manifest (the experimental host).
FROM ubuntu@sha256:08ea48a03a3e78ebc7cd526e6a275053223aadd88bfc09cc49b06d5281525fde

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update -o APT::Update::Error-Mode=any \
    && apt-get install -y --no-install-recommends \
      gcc-11 \
      clang-14 \
      llvm-14 \
      libclang-common-14-dev \
      python3 \
      python3.10 \
      ca-certificates \
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
