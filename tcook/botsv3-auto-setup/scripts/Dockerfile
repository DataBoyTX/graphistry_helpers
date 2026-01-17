# Splunk Enterprise with BOTSv3 Dataset
# Automated setup for Boss of the SOC v3 CTF Challenge
# Includes all required add-ons for proper field extraction
FROM ubuntu:22.04

LABEL maintainer="Splunk BOTSv3 Docker Setup"
LABEL description="Splunk Enterprise with pre-loaded BOTSv3 dataset and all required add-ons"

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Splunk configuration
ENV SPLUNK_HOME=/opt/splunk
ENV SPLUNK_START_ARGS="--accept-license"
ENV SPLUNK_PASSWORD=changeme123
ENV SPLUNK_USER=admin

# Install required packages
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    procps \
    net-tools \
    vim \
    tar \
    gzip \
    ca-certificates \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Create splunk user
RUN useradd -m -s /bin/bash splunk

# Download and install Splunk Enterprise
WORKDIR /tmp
RUN wget -O splunk-9.1.0.2-b6436b649711-linux-2.6-amd64.deb \
    "https://download.splunk.com/products/splunk/releases/9.1.0.2/linux/splunk-9.1.0.2-b6436b649711-linux-2.6-amd64.deb" && \
    echo "f3299482a6115c3695ea95216c0427c64d023013159221b005b92d16a34aff49996d691669729bcfa992788a40e3fdcc0c69b6f819931acd0d60e831db47b00f  splunk-9.1.0.2-b6436b649711-linux-2.6-amd64.deb" | sha512sum -c - && \
    dpkg -i splunk-9.1.0.2-b6436b649711-linux-2.6-amd64.deb && \
    rm splunk-9.1.0.2-b6436b649711-linux-2.6-amd64.deb

# Download BOTSv3 dataset
RUN wget -O botsv3_data_set.tgz \
    "https://botsdataset.s3.amazonaws.com/botsv3/botsv3_data_set.tgz" && \
    echo "d7ccca99a01cff070dff3c139cdc10eb  botsv3_data_set.tgz" | md5sum -c - && \
    tar -xzf botsv3_data_set.tgz -C ${SPLUNK_HOME}/etc/apps/ && \
    rm botsv3_data_set.tgz

# Create directory for add-ons
RUN mkdir -p /tmp/addons

# Copy pre-downloaded add-ons (if available)
# These are copied from resources/splunk-add-ons/ directory
COPY splunk-add-ons/ /tmp/addons/

# Install all available add-ons
# Each add-on tarball extracts to its app directory
RUN for addon in /tmp/addons/*.tgz; do \
        if [ -f "$addon" ]; then \
            echo "Installing add-on: $addon"; \
            tar -xzf "$addon" -C ${SPLUNK_HOME}/etc/apps/; \
        fi; \
    done && \
    rm -rf /tmp/addons

# Install add-ons from zip files (if any)
RUN for addon in /tmp/addons/*.zip 2>/dev/null; do \
        if [ -f "$addon" ]; then \
            echo "Installing add-on: $addon"; \
            unzip -q "$addon" -d ${SPLUNK_HOME}/etc/apps/; \
        fi; \
    done 2>/dev/null || true

# Create user-seed.conf for initial admin credentials
RUN mkdir -p ${SPLUNK_HOME}/etc/system/local && \
    echo "[user_info]" > ${SPLUNK_HOME}/etc/system/local/user-seed.conf && \
    echo "USERNAME = ${SPLUNK_USER}" >> ${SPLUNK_HOME}/etc/system/local/user-seed.conf && \
    echo "PASSWORD = ${SPLUNK_PASSWORD}" >> ${SPLUNK_HOME}/etc/system/local/user-seed.conf

# Configure Splunk web and REST API settings
RUN echo "[settings]" > ${SPLUNK_HOME}/etc/system/local/web.conf && \
    echo "enableSplunkWebSSL = false" >> ${SPLUNK_HOME}/etc/system/local/web.conf && \
    echo "httpport = 8000" >> ${SPLUNK_HOME}/etc/system/local/web.conf

# Configure server settings
RUN echo "[general]" > ${SPLUNK_HOME}/etc/system/local/server.conf && \
    echo "serverName = splunk-botsv3" >> ${SPLUNK_HOME}/etc/system/local/server.conf && \
    echo "" >> ${SPLUNK_HOME}/etc/system/local/server.conf && \
    echo "[httpServer]" >> ${SPLUNK_HOME}/etc/system/local/server.conf && \
    echo "acceptFrom = *" >> ${SPLUNK_HOME}/etc/system/local/server.conf

# Configure indexes to work with overlay filesystem
RUN echo "[default]" > ${SPLUNK_HOME}/etc/system/local/indexes.conf && \
    echo "homePath.maxDataSizeMB = 50000" >> ${SPLUNK_HOME}/etc/system/local/indexes.conf && \
    echo "minFreeSpace = 0" >> ${SPLUNK_HOME}/etc/system/local/indexes.conf

# Set ownership
RUN chown -R splunk:splunk ${SPLUNK_HOME}

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose ports
# 8000 - Splunk Web
# 8089 - Splunk REST API (splunkd)
# 9997 - Splunk Forwarder receiving port
# 8088 - HTTP Event Collector
EXPOSE 8000 8089 9997 8088

# Set working directory
WORKDIR ${SPLUNK_HOME}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/en-US/account/login || exit 1

# Run as splunk user
USER splunk

ENTRYPOINT ["/entrypoint.sh"]
CMD ["start"]
