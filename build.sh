#!/usr/bin/env bash
# build.sh

# Exit on error
set -o errexit

# Add Microsoft repository
curl https://packages.microsoft.com/keys/microsoft.asc > /etc/apt/trusted.gpg.d/microsoft.asc
curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list

# Install prerequisites
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    unixodbc \
    unixodbc-dev \
    libodbc1 \
    odbcinst1debian2 \
    tdsodbc \
    freetds-dev \
    freetds-bin \
    freetds-common \
    libct4

# Install Microsoft ODBC driver
ACCEPT_EULA=Y DEBIAN_FRONTEND=noninteractive apt-get install -y msodbcsql18

# Configure ODBC drivers
odbcinst -i -s -f /usr/share/tdsodbc/freetds.conf

# Create required directories if they don't exist
mkdir -p /opt/render/project/src/src/image

# Install Python dependencies
pip install -r requirements.txt