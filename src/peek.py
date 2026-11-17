"""CITIRE fara efecte: cate mesaje sunt in coada si ce contin.

Cu VisibilityTimeout=0 mesajele citite raman imediat vizibile, deci
consumatorul nu este afectat.

Exemple:
  python src/peek.py           # coada principala
  python src/peek.py --dlq     # dead-letter queue
"""
import argparse

from config import DLQ_NAME, QUEUE_NAME, queue_url, sqs_client


def count_messages(sqs, url):
    attrs = sqs.get_queue_attributes(
        QueueUrl=url,
        AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"],
    )["Attributes"]
    return int(attrs["ApproximateNumberOfMessages"]), int(attrs["ApproximateNumberOfMessagesNotVisible"])


def peek(sqs, url, max_messages=10):
    resp = sqs.receive_message(
        QueueUrl=url,
        MaxNumberOfMessages=max_messages,
        VisibilityTimeout=0,
        AttributeNames=["ApproximateReceiveCount"],
    )
    return resp.get("Messages", [])


def main():
    parser = argparse.ArgumentParser(description="Afiseaza continutul cozii fara a-l modifica")
    parser.add_argument("--dlq", action="store_true", help="uita-te in dead-letter queue")
    args = parser.parse_args()

    name = DLQ_NAME if args.dlq else QUEUE_NAME
    sqs = sqs_client()
    url = queue_url(sqs, name)

    vizibile, ascunse = count_messages(sqs, url)
    print(f"Coada '{name}': {vizibile} mesaje vizibile, {ascunse} in procesare")
    for m in peek(sqs, url):
        citiri = m.get("Attributes", {}).get("ApproximateReceiveCount", "?")
        print(f"  - {m['MessageId']}  (citit de {citiri} ori)  {m['Body']}")


if __name__ == "__main__":
    main()
