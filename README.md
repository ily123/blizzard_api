Draft - there are mistakes in this README...
---

# M+ Meta Watch 
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Backend code for collection and storage of Blizzard's M+ leaderboard data.
## Installation
This thing runs on python3, and uses only a few high-level dependencies.

1. Install Python3, any version 3.6 and up should be fine
    ```
    sudo apt-get install python3.6
    ```
2. Use your favorite env manager to create and active a virtual environment
    ```
    mkdir envs  # I keep my environments under /home/envs
    cd envs
    python3.6 -m venv metawatch  # will createa 'metawatch' folder under env/
    source /home/envs/metawatch/bin/activate
    cd ~
    ```
3. Clone m2watch-backend repo to your machine
    ```
    git clone https://github.com/ily123/blizzard_api
    ```
4. Install dependencies using ```requirements.txt```
    ```
    pip install -r requirements.txt
    ```
## Usage
## License

