Draft - there are mistakes in this README...
---

# M+ Meta Watch 

Backend code for collection and storage of Blizzard's M+ leaderboard data.

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Overview 
    The codes in this repo these things:
    1) Retrieve this week's leaderboard runs
    2) Queries Blizzard's API for M+ leaderbords
    3) Clean, uniq, and assign identifiers to runs found in the leaderboards
    4) Take a diff between existing runs and incoming runs
    5) Push the diff into the database
    6) Summarize data in the DB and push it into an SQLite file, which we can 
    then embed with the front-end web app (Note: Ideally, delivering data to the 
    front end would be done via an API, but I don't know how to write one yet.)

    ```
    Blizzard M+ API -> Worker RAM -> Digest -> Insert into MySQL DB
    ```

## Installation
This thing runs on python3, and uses only a few high-level dependencies.

1. Install Python3, any version 3.6 and up should be fine
    ```
    sudo apt-get install python3.6
    ```
2. Use your favorite env manager to create and active a blank virtual environment
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
    cd metawatch
    pip install -r requirements.txt
    ```
    or manually
    ```
    pip install numpy
    pip install pandas
    pip install requests
    pip install mysql-connector-python
    #--do i need these? they are listed in requirements.txt
    #--pip install scipy
    #--pip install jupyter
    #--pip install plotly
    #--pip install matplotlib
    ```

## Configuration


## Usage
## License

