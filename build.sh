#!/bin/bash
# Install ODBC dependencies
apt-get update
apt-get install -y unixodbc unixodbc-dev
apt-get install -y gnupg2
curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list
apt-get update
ACCEPT_EULA=Y apt-get install -y msodbcsql18
# Install Python dependencies
pip install -r requirements.txt