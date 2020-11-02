import sys

sys.path.append("/home/ubuntu/CodeRepos/blizzard_api/")

from datetime import timedelta
import datetime

# The DAG object; we'll need this to instantiate a DAG
from airflow import DAG
# Operators; we need this to operate!
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago

import pipeline
# These args will get passed on to each operator
# You can override them on a per-task basis during operator initialization
default_args = {
    'owner': 'ily123',
    'depends_on_past': False,
    'start_date': datetime.datetime(year=2020, month=10, day=31, hour=0, minute=20),
    'end_date': datetime.datetime(year=2021, month=10, day=31, hour=0, minute=20),
    #'email': ['airflow@example.com'],
    #'email_on_failure': False,
    #'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=3),
    # 'queue': 'bash_queue',
    # 'pool': 'backfill',
    # 'priority_weight': 10,
    # 'end_date': datetime(2016, 1, 1),
    # 'wait_for_downstream': False,
    # 'dag': dag,
    # 'sla': timedelta(hours=2),
    # 'execution_timeout': timedelta(seconds=300),
    # 'on_failure_callback': some_function,
    # 'on_success_callback': some_other_function,
    # 'on_retry_callback': another_function,
    # 'sla_miss_callback': yet_another_function,
    # 'trigger_rule': 'all_success'
}
dag = DAG(
    'metawatch',
    default_args=default_args,
    description='A simple tutorial DAG',
    schedule_interval=timedelta(hours=1),
)

t1 = PythonOperator(
    task_id = "metawatch_loop",
    python_callable=pipeline.get_data,
    dag=dag
)

t1
