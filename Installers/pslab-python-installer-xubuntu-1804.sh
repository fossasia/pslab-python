#!/bin/bash

# Define colors
GREENBOLD='\e[1m\e[32m'
GREEN='\e[32m'
CYAN='\e[96m'
MAGENTA='\e[95m'
BLUE='\e[94m'
YELLOW='\033[1;33m'
ORANGE='\033[0;33m'
NOCOLOR='\033[0m'

echo -e "${GREENBOLD}Welcome to PSLab Python Library Installer...${NOCOLOR}"
echo -e "${YELLOW}Setup will start now. It will take a while to complete but please be around ...${NOCOLOR}"
# Create a temporary folder and move inside to download and install stuff
sudo rm -rf pslab_temp
mkdir pslab_temp && cd pslab_temp
echo -e "${ORANGE}Updating the package manager ...${NOCOLOR}"
# Updating apt-get package manager to have latest software
sudo apt-get update
# Download and extract Python 3.7.3
echo -e "${ORANGE}Downloading Python 3.7.3${NOCOLOR}"
wget https://www.python.org/ftp/python/3.7.3/Python-3.7.3.tgz
echo -e "${ORANGE}Extracting Python source file${NOCOLOR}"
tar -xvf Python-3.7.3.tgz >/dev/null
echo -e "${ORANGE}Removing source file${NOCOLOR}"
rm -rf Python-3.7.3.tgz >/dev/null
# Install dependant packages
echo -e "${ORANGE}Installing dependant packages ...${NOCOLOR}"
sudo apt-get install gcc zlib1g-dev libffi-dev -y
sudo apt-get install make -y
sudo apt-get install libssl-dev libncurses5-dev libsqlite3-dev libreadline-dev libtk8.5 libgdm-dev libdb4o-cil-dev libpcap-dev -y
# Install Python 3.7.3
echo -e "${ORANGE}Installing Python-3.7.3 ...${NOCOLOR}"
cd Python-3.7.3
./configure
make
make install
cd ..
# Upgrade pip3
echo -e "${ORANGE}Upgrading PIP ...${NOCOLOR}"
python3 -m pip install --upgrade pip
# Install and upgrade numpt
echo -e "${ORANGE}Installing NumPy ...${NOCOLOR}"
python3 -m pip install numpy --upgrade
# Install and upgrade PySerial
echo -e "${ORANGE}Installing PySerial ...${NOCOLOR}"
python3 -m pip install pyserial --upgrade
# Install and upgrade SetupTools
echo -e "${ORANGE}Installing SetupTools ...${NOCOLOR}"
python3 -m pip install setuptools --upgrade
# Install Git
echo -e "${ORANGE}Installing Git ...${NOCOLOR}"
sudo apt-get install git
#######################################################
echo -e "${YELLOW}All dependencies have been installed. Starting PSLab library installation ...${NOCOLOR}"
# Clone pslab-python repository
git clone -b master https://github.com/fossasia/pslab-python.git
# Move into pslab-python folder
cd pslab-python
# Execute installation commands
sudo make clean
make all
sudo make install
# Move out of pslab-python directory and delete it
cd .. && sudo rm -rf pslab-python
# Move out from temp installation directory and delete it
cd .. && rm -rf pslab_temp
# Print completion message
echo -e "${BLUE}Installation is now complete. Please check the log for any errors ...${NOCOLOR}"
