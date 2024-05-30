from datetime import timedelta, datetime
from airflow.decorators import dag, python_task
from google.cloud import storage
import requests
import pandas as pd
import logging
import pendulum
from utils.gcp import gcs
import os
from utils.discord_notifications import DiscordNotifier
from dotenv import load_dotenv

load_dotenv()
discord_conn_id = os.getenv("discord_webhook")

default_args = {
    'owner': 'TIR101_G2',
    'retries': 0,
    'retry_delay': timedelta(minutes=1)
}


def notify_success(context):
    discord_notifier = DiscordNotifier(
        discord_conn_id=discord_conn_id,
        text="DAG has succeeded!",
        username="Airflow Bot"
    )
    discord_notifier.notify(context)


def notify_failure(context):
    discord_notifier = DiscordNotifier(
        discord_conn_id=discord_conn_id,
        text="DAG has failed!",
        username="Airflow Bot"
    )
    discord_notifier.notify(context)


@dag(
    # basic setting for all dags
    dag_id='ubike_rt_to_gcs',
    default_args=default_args,
    schedule_interval='*/10 * * * *',
    start_date=datetime(2024, 4, 10),
    tags=["reoccuring", "data_ingestion"],
    on_success_callback=notify_success,  # 在 DAG 成功時調用
    on_failure_callback=notify_failure,   # 在 DAG 失敗時調用
    catchup=False)
def bike_realtime_to_gcs():
    # setup the client that will be use in the dags
    gcs_client = storage.Client()

    @python_task
    def get_rt_data():
        # get data from url
        resp = requests.get(
            'https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json')  # noqa
        single_result = resp.json()
        single_result = pd.json_normalize(single_result)

        # set up the required names for inserting the data into GCS
        now = pendulum.now('Asia/Taipei').format("MM_DD_YYYY/HH_mm")
        # bucket_name = f"youbike_realtime_andy"
        bucket_name = f"testbucket0204"
        filename = f'dt={now}.csv'

        # inserting the file into GCS
        result = gcs.upload_df_to_gcs(
            gcs_client, bucket_name, filename, single_result)
        if result:
            logging.info(f'file: {filename} created!')

    # call the previously defined functions
    get_rt_data()


# this actually runs the whole DAG
bike_realtime_to_gcs()
