"""INSERARE: producatorul trimite comenzi in coada.

Exemple:
  python src/producer.py                 # 3 comenzi valide
  python src/producer.py --count 5       # 5 comenzi valide
  python src/producer.py --invalid       # un mesaj invalid (nu e JSON) -> va ajunge in DLQ
"""
import argparse
import json
import random
import uuid
from datetime import datetime, timezone

from config import queue_url, sqs_client

PRODUSE = ["laptop", "mouse", "tastatura", "monitor", "casti"]


def comanda_noua():
    return {
        "id": str(uuid.uuid4())[:8],
        "produs": random.choice(PRODUSE),
        "cantitate": random.randint(1, 3),
        "creata_la": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def send_order(sqs, url, comanda):
    resp = sqs.send_message(QueueUrl=url, MessageBody=json.dumps(comanda))
    return resp["MessageId"]


def send_invalid(sqs, url, body="nu-e-json"):
    return sqs.send_message(QueueUrl=url, MessageBody=body)["MessageId"]


def main():
    parser = argparse.ArgumentParser(description="Trimite comenzi in coada SQS")
    parser.add_argument("--count", type=int, default=3, help="cate comenzi valide (implicit 3)")
    parser.add_argument("--invalid", action="store_true", help="trimite un singur mesaj invalid")
    args = parser.parse_args()

    sqs = sqs_client()
    url = queue_url(sqs)

    if args.invalid:
        print(f"Trimis mesaj INVALID, MessageId={send_invalid(sqs, url)}")
        return

    for _ in range(args.count):
        comanda = comanda_noua()
        mid = send_order(sqs, url, comanda)
        print(f"Trimis {comanda}  MessageId={mid}")


if __name__ == "__main__":
    main()
