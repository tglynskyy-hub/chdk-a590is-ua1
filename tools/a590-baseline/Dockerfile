FROM debian:bullseye-slim

# Fixed package archive; compiler matches the upstream autobuild environment.
RUN printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/20251229T000000Z/ bullseye main\n' > /etc/apt/sources.list \
 && rm -f /etc/apt/sources.list.d/* \
 && apt-get update \
 && apt-get install --no-install-recommends -y gcc gcc-arm-none-eabi libc6-dev make zip python3 ca-certificates \
 && rm -rf /var/lib/apt/lists/*
ENV LC_ALL=C TZ=UTC SOURCE_DATE_EPOCH=1766992455
WORKDIR /src
