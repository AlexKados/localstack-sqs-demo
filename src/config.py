"""Configurarea comuna: clientul SQS si numele cozilor.

Codul NU contine adresa LocalStack scrisa direct in logica: o citeste din
variabila de mediu AWS_ENDPOINT_URL (ca SDK-urile AWS). Daca variabila lipseste,
folosim implicit LocalStack, ca un script rulat din greseala sa nu ajunga
niciodata la AWS-ul real.
"""
import os

import boto3

ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL", "http://localhost.localstack.cloud:4566")
REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

QUEUE_NAME = os.environ.get("QUEUE_NAME", "comenzi")
DLQ_NAME = os.environ.get("DLQ_NAME", "comenzi-dlq")

# Dupa cate citiri esuate un mesaj ajunge in dead-letter queue
MAX_RECEIVE_COUNT = int(os.environ.get("MAX_RECEIVE_COUNT", "3"))
# Cat timp un mesaj citit ramane ascuns (secunde). Mic, ca demo-ul sa fie rapid.
VISIBILITY_TIMEOUT = int(os.environ.get("VISIBILITY_TIMEOUT", "5"))


def sqs_client():
    return boto3.client(
        "sqs",
        endpoint_url=ENDPOINT_URL,
        region_name=REGION,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", "test"),
    )


def queue_url(sqs, name=None):
    return sqs.get_queue_url(QueueName=name or QUEUE_NAME)["QueueUrl"]
