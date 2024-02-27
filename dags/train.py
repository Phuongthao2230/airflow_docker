from datetime import datetime, timedelta
import json
import pandas as pd
from airflow import DAG
from airflow.operators.python import PythonOperator
import ssl
from urllib.request import Request, urlopen
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import base64

ssl._create_default_https_context = ssl._create_unverified_context

def craw_stock_price(**kwargs):
    to_date = kwargs["to_date"]
    from_date = "2000-01-01"
    stock_price_list = []  # Use a list to store stock prices

    stock_code = "DIG"

    url = "https://finfo-api.vndirect.com.vn/v4/stock_prices?sort=date&q=code:{}~date:gte:{}~date:lte:{}&size=9990&page=1".format(stock_code, from_date, to_date)
    print(url)

    req = Request(url, headers={'User-Agent': 'Mozilla / 5.0 (Windows NT 6.1; WOW64; rv: 12.0) Gecko / 20100101 Firefox / 12.0'})
    req.add_header("Authorization", "Basic %s" % "ABCZYXX")
    x = urlopen(req, timeout=10).read()

    json_x = json.loads(x)['data']

    for stock in json_x:
        stock_price_list.append(stock)  # Append each stock to the list

    stock_price_df = pd.DataFrame(stock_price_list)  # Create DataFrame from the list
    stock_price_df.to_csv("/home/airflow/stock_price.csv", index=None)
    return True


def email():
    out_csv_file_path = '/home/airflow/stock_price.csv'
    message = Mail(
        from_email='ainoodle.tech@gmail.com',
        to_emails='phuongthaoadn@gmail.com',
        subject='Your file is here!',
        html_content='<img src="https://miai.vn/wp-content/uploads/2022/01/Logo_web.png"> Dear Customer,<br>Welcome to Mi AI. Your file is in attachment<br>Thank you!'
    )

    with open(out_csv_file_path, 'rb') as f:
        data = f.read()
    encoded_file = base64.b64encode(data).decode()

    attachedFile = Attachment(
        FileContent(encoded_file),
        FileName('data.csv'),
        FileType('text/csv'),
        Disposition('attachment')
    )
    message.attachment = attachedFile

    try:
        sg = SendGridAPIClient("Your_SendGrid_API_Key_Here")
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
        print(datetime.now())
    except Exception as e:
        print(e)

    return True

dag = DAG(
    'miai_dag',
    default_args={
        'email': ['phuongthaoadn@gmail.com'],
        'email_on_failure': True,
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
    },
    description='A ML training pipeline DAG',
    schedule_interval=timedelta(days=1),
    start_date=datetime.today() - timedelta(days=1),
    tags=['thangnc']
)

crawl_data = PythonOperator(
    task_id='crawl_data',
    python_callable=craw_stock_price,
    op_kwargs={"to_date": "{{ ds }}"},
    dag=dag
)

email_operator = PythonOperator(
    task_id='email_operator',
    python_callable=email,
    dag=dag
)

crawl_data >> email_operator
