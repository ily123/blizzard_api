### Setting up airflow on EC2 worker
---

Setting up airflow has been non-trivial, so I am leaving instructions here just in case.

**General notes**

1. I ran into an issue resolving Python script dependencies. The pipeline requires tasks to
to be run in different environments. We can achieve that in 4 different ways:
    * Install all dependencies under a single environment, and run airflow from there.
    This is doable for small pipelines like mine, but doesn't seem like good practise.
    * Use PythonVirtualenvOperator instead of PythonOperator as described [here](https://medium.com/@iashishhere/how-did-i-resolved-pip-package-dependency-issue-in-apache-airflow-8e0b1e5a067c). The env operator takes in a list
    of pip packages as one of its args. Every time it runs, it creates a virtual env and
    installs the packages. Once the task is done, it deletes the env. From what I understand,
    it does it every single time. Constantly reinstalling the packages seems wasteful.
    * **The solution I went with:** Instead of using Python operators, use Bash operators, and
    in the body of the command define the path of the python interpreter you want to
    execute the command. This is naive, and has its own issues, but easy to implement.
    So I did this.
    * The solution that I should probably be using: I need to containerize my pipeline
    and use airflow's DockerOperator. This way, env management isnt't an issue. Just
    gotta learn Docker :)

---
**Installation**

* Create a separate python3 env for airflow
* Activate airflow env, and install airflow:

	```
	pip install apache-airflow==1.10.12 \ --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-1.10.12/constraints-3.7.txt"
	```
* **Note:** Whenever you execute airflow commands it will create ```/home/<user>/airflow/``` folder to store its configurations and dags. Let it do it. If you want a different folder, tell it where with ```export AIRFLOW_HOME=<desired airflow foler>```. I found it easier to just let airflow live in /home.
* Test that airflow installed correctly:
	* do ```airflow -help```
	* After running ```airflow -help``` there should be an ```airflow/``` dir in your home.
	* if it errors out, see full installation tutorial [here](https://airflow.apache.org/docs/stable/installation.html)
---
**Spin up the dashboard server**
* Airflow needs a db to store its tasks, initialize it with ```airflow initdb```. This will create a SQLite file inside ```airflow/```.
* Spin up the airflow control dashboard with ```airflow webserver -port 4000``` (Go to ```localhost:4000``` to see if it's there). Note that the webserver will not launch unless you've initialized the db.
* At this point, airflow will complain that the ```scheduler``` is not running. We will set it up later.
---

**Add your pipeline script**
* Add your pipeline script (```metawatch_bash.py```) to ```airflow/dags/```. This is where airflow will look for your pipelines by default.
* Test that the script doesn't throw errors when importing:
	```
	python metawatch_bash.py
	```
* If there are no errors, you can test each task in the pipeline, as described in the tutorial:
	```
	airflow test metawatch_bash get_data 2020-01-01
	```
	Note that the log isn't printed to terminal until the task is complete.
	
**Launch scheduler and start pipeline**
* To start the scheduler, the thing that actually runs the tasks, do
    ```
    airflow scheduler
    ```
* Now, go to the dashboard (your pipeline should be there). Click your dag's on/off switch to turn on. It should be running now.
* Note: the pipeline will launch at ```start_date``` + ```interval```. So if you need to run it now, set ```start_time``` to now - ```interval```. These are the args in the airflow script.
---
**To run all this in the background**

As described to run this pipeline you'll need 2 open terminal windows connected to the EC2
worker (one terminal for scheduler, and one for webserver). As soon as you close the terminals or the
connection breaks, airflow will stop executing.

There are two solutions to this. One is to run airflow in the background like this:
```
nohup airflow webserver -p 4000 >> webserver.log &
nohup airflow scheduler -p 4000 >> webserver.log &
```
Now, you should be able to log off. If a server crashes, though, you have to restart these manually.

The second option is to set up airflow as a
service. This way, whenever the node crashes, airflow will launch automatically. (But
will the pipeline restart on its own? I need to look into this.)

**To kill:**

Use htop. I think you can stop gracefully it if it's ran as a service.
