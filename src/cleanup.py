"""STERGERE: goleste sau sterge cozile.

Exemple:
  python src/cleanup.py --purge    # sterge toate mesajele, pastreaza cozile
  python src/cleanup.py            # sterge ambele cozi
"""
import argparse

from config import DLQ_NAME, QUEUE_NAME, queue_url, sqs_client


def main():
    parser = argparse.ArgumentParser(description="Goleste sau sterge cozile demo-ului")
    parser.add_argument("--purge", action="store_true", help="doar goleste cozile")
    args = parser.parse_args()

    sqs = sqs_client()
    for name in (QUEUE_NAME, DLQ_NAME):
        try:
            url = queue_url(sqs, name)
        except sqs.exceptions.QueueDoesNotExist:
            print(f"Coada '{name}' nu exista")
            continue
        if args.purge:
            sqs.purge_queue(QueueUrl=url)
            print(f"Golita: {name}")
        else:
            sqs.delete_queue(QueueUrl=url)
            print(f"Stearsa: {name}")


if __name__ == "__main__":
    main()
