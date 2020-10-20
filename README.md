Draft - there are mistakes in this README...
---

# M+ Meta Watch 

Backend code for collection and storage of Blizzard's Mythic+ leaderboard data.

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Overview 

![test](mw_pic.svg) <!-- .element height="50%" width="50%" -->


The pipeline assembled from the codes in this repo does these things:

1. Retrieve IDs of M+ runs recorded in our database (for the current week)
2. Query Blizzard's API for current week's M+ leaderbords
3. Parse leaderboard jsons, assign unique IDs to all relevant records
4. Find novel records in the parse results by comparing them to output of step (1)
5. Push novel records into the database
6. Summarize data in the DB and pipe it into an SQLite file, which we can 
then pass to the front end (see this repo).

The code is fairly modular/generic, so you can build things differently. See repo structure and docstrings for more detail.

## Repo struct

```
    ├── data/                      # saves SQLite summary here, empty
    ├── notebooks/                 # research & test nbs; for posterity, PATHs broken
    ├── sql_scripts/               # SQL scripts to create empty DB tables
    ├── blizzard_api.py            # module with fetch/parse logic
    ├── blizzard_credentials.py    # authorization module
    ├── mplusdb.py                 # database connector
    ├── populate_realm_table.py    # <<< not sure if this is needed
    ├── README.md                  
    ├── requirements.txt          
    ├── summarize.py               # script to create / update / export summary data
    ├── tasks.py                   # high-level pipeline to populate the DB with data
    └── utils.py                   # utility methods
```

## Prerequisite: MySQL database
The code in this repo talks to a MySQL database, and the database has to be set up first.
How you do that is up to you. Here is the guide I used to set up a local MySQL database. And here is the guide to any number of cloud solutions "GOOGLE: set up MySQL database in the cloud."

The version I am using locally for development is:

```
Ver 8.0.21 for Linux on x86_64 (MySQL Community Server - GPL)
```
And on AWS RDS for "production":
```
aws-ver-...
```
All of the SQL operations are very generic, so I don't think it matters what version you use as long as it's 8+.


## Installation 
This thing runs on python3, and uses only a few high-level dependencies.

1. Install ```mysql``` utility for Linux:
    ```
    sudo apt-get FIND PACKAGE NAME
    ```
    Linux uses this to talk to the database.

2. Install Python3, any version 3.6 and up should be fine
    ```
    sudo apt-get install python3.6
    ```
3. Use your favorite env manager to create and active a blank virtual environment
    ```
    mkdir envs  # I keep my environments under /home/envs
    cd envs
    python3.6 -m venv metawatch  # will createa 'metawatch' folder under env/
    source /home/envs/metawatch/bin/activate
    cd ~
    ```
4. Clone m2watch-backend repo to your machine
    ```
    git clone https://github.com/ily123/blizzard_api
    ```
5. Install dependencies using ```requirements.txt```
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
    ```
6. Don't try to run anything yet. You still need to configure DB connection, and authorization token for API access.


## Configuration
Once you got a DB and 

## Usage
## License

