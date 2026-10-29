FROM debian:bullseye-slim@sha256:e5b6442dd2e9684cf5e87d8338b5968f3b348636fc0be6d7850a381e3731a2bd

# Fixed package archive; compiler matches the upstream autobuild environment.
RUN printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/20251229T000000Z/ bullseye main\n' > /etc/apt/sources.list \
 && rm -f /etc/apt/sources.list.d/* \
 && apt-get update \
 && apt-get install --no-install-recommends --allow-downgrades -y libc6=2.31-13+deb11u11 libc-bin=2.31-13+deb11u11 gcc gcc-arm-none-eabi libc6-dev make zip python3 ca-certificates \
 && rm -rf /var/lib/apt/lists/*
ENV LC_ALL=C TZ=UTC SOURCE_DATE_EPOCH=1766992455
WORKDIR /src
