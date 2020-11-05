import datetime
# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
# Operators; we need this to operate!
from airflow.operators.bash_operator import BashOperator

# These args will get passed on to each operator
# You can override them on a per-task basis during operator initialization
default_args = {
    'owner': 'ily123',
    'depends_on_past': False,
    'start_date': datetime.datetime(year=2020, month=11, day=3, hour=2, minute=3),
    'end_date': datetime.datetime(year=2021, month=10, day=31, hour=0, minute=50),
    #'email': ['airflow@example.com'],
    #'email_on_failure': False,
    #'email_on_retry': False,
    'retries': 1,
    'retry_delay': datetime.timedelta(minutes=3),
}

#define the dag object
dag = DAG(
    'metawatch_bash',
    default_args=default_args,
    description='m+ data scraper',
    schedule_interval=datetime.timedelta(hours=1),
)


# bash commands
get_data = "cd /home/ubuntu/CodeRepos/metawatch/ && " + \
               "/home/ubuntu/CodeRepos/envs/scraper/bin/python " + \
               "/home/ubuntu/CodeRepos/metawatch/pipeline.py"

copy_data = "cp /home/ubuntu/CodeRepos/metawatch/data/summary.sqlite " + \
            "/home/ubuntu/CodeRepos/metawatch-dash/data/summary.sqlite"

deploy_data_to_eb = "cd /home/ubuntu/CodeRepos/metawatch-dash/ && " + \
    "source /home/ubuntu/CodeRepos/envs/dash/bin/activate && " + \
    "eb deploy && " + \
    "deactivate"


t1 = BashOperator(
    task_id='get_data',
    bash_command=get_data,
    dag=dag,
)

t2 = BashOperator(
    task_id='copy_data',
    bash_command=copy_data,
    dag=dag,
)

t3 = BashOperator(
    task_id='deploy_data_to_eb',
    bash_command=deploy_data_to_eb,
    dag=dag,
)

t1 >> t2 >> t3
