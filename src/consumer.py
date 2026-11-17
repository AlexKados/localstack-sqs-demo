"""CONSUMARE + STERGERE: consumatorul citeste, proceseaza si sterge comenzile.

Un mesaj este sters DOAR daca a fost procesat cu succes. Un mesaj invalid nu
este sters: dupa VisibilityTimeout redevine vizibil, este reincercat, iar dupa
MAX_RECEIVE_COUNT incercari SQS il muta singur in dead-letter queue.

Exemple:
  python src/consumer.py             # ruleaza pana cand coada ramane goala
  python src/consumer.py --forever   # asculta continuu (Ctrl+C pentru oprire)
"""
import argparse
import json

from config import queue_url, sqs_client

CAMPURI = ("id", "produs", "cantitate")


class ComandaInvalida(Exception):
    pass


def proceseaza(body):
    """Logica de business: valideaza comanda si o 'onoreaza'."""
    try:
        comanda = json.loads(body)
    except json.JSONDecodeError as e:
        raise ComandaInvalida(f"nu este JSON: {body!r}") from e
    if not isinstance(comanda, dict) or any(c not in comanda for c in CAMPURI):
        raise ComandaInvalida(f"lipsesc campuri obligatorii {CAMPURI}: {body!r}")
    if not isinstance(comanda["cantitate"], int) or comanda["cantitate"] <= 0:
        raise ComandaInvalida(f"cantitate invalida: {comanda['cantitate']!r}")
    return comanda


def poll_once(sqs, url, wait_seconds=2):
    """O citire din coada. Intoarce (procesate, esuate, mesaje_primite)."""
    resp = sqs.receive_message(
        QueueUrl=url,
        MaxNumberOfMessages=10,
        WaitTimeSeconds=wait_seconds,  # long polling
        AttributeNames=["ApproximateReceiveCount"],
    )
    mesaje = resp.get("Messages", [])
    ok = fail = 0
    for m in mesaje:
        incercare = m.get("Attributes", {}).get("ApproximateReceiveCount", "?")
        try:
            c = proceseaza(m["Body"])
        except ComandaInvalida as e:
            fail += 1
            print(f"  [EROARE, incercarea {incercare}] {e} -> mesajul NU se sterge")
            continue
        sqs.delete_message(QueueUrl=url, ReceiptHandle=m["ReceiptHandle"])
        ok += 1
        print(f"  [OK] comanda {c['id']}: {c['cantitate']} x {c['produs']} -> procesata si stearsa")
    return ok, fail, len(mesaje)


def main():
    parser = argparse.ArgumentParser(description="Consuma comenzile din coada SQS")
    parser.add_argument("--forever", action="store_true", help="nu se opreste cand coada e goala")
    parser.add_argument("--empty-polls", type=int, default=3,
                        help="se opreste dupa atatea citiri goale la rand (implicit 3)")
    args = parser.parse_args()

    sqs = sqs_client()
    url = queue_url(sqs)
    total_ok = total_fail = goale = 0
    print(f"Consumatorul asculta pe {url}")
    try:
        while args.forever or goale < args.empty_polls:
            ok, fail, n = poll_once(sqs, url)
            total_ok += ok
            total_fail += fail
            goale = goale + 1 if n == 0 else 0
    except KeyboardInterrupt:
        pass
    print(f"Gata: {total_ok} procesate, {total_fail} esuari")


if __name__ == "__main__":
    main()
