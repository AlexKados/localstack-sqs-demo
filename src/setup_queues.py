"""CREARE: coada principala `comenzi` si dead-letter queue-ul `comenzi-dlq`.

Rulare:  python src/setup_queues.py
"""
import json

from config import DLQ_NAME, MAX_RECEIVE_COUNT, QUEUE_NAME, VISIBILITY_TIMEOUT, sqs_client


def create_queues(sqs=None):
    sqs = sqs or sqs_client()

    # 1. Dead-letter queue: aici ajung mesajele care esueaza de prea multe ori
    dlq_url = sqs.create_queue(QueueName=DLQ_NAME)["QueueUrl"]
    dlq_arn = sqs.get_queue_attributes(QueueUrl=dlq_url, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]

    # 2. Coada principala, legata de DLQ prin RedrivePolicy
    url = sqs.create_queue(
        QueueName=QUEUE_NAME,
        Attributes={
            "VisibilityTimeout": str(VISIBILITY_TIMEOUT),
            "RedrivePolicy": json.dumps(
                {"deadLetterTargetArn": dlq_arn, "maxReceiveCount": str(MAX_RECEIVE_COUNT)}
            ),
        },
    )["QueueUrl"]
    return url, dlq_url


if __name__ == "__main__":
    url, dlq_url = create_queues()
    print(f"Coada principala : {url}")
    print(f"Dead-letter queue: {dlq_url}")
