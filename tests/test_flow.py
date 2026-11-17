"""Teste automate ale fluxului complet, ruland pe un SQS simulat (moto).

Rulare:  pip install -r requirements-dev.txt && pytest -v
"""
import os
import sys
import time

import pytest

os.environ.update(
    AWS_ACCESS_KEY_ID="test", AWS_SECRET_ACCESS_KEY="test", AWS_DEFAULT_REGION="us-east-1",
    VISIBILITY_TIMEOUT="1", MAX_RECEIVE_COUNT="3",
)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import boto3  # noqa: E402
from moto import mock_aws  # noqa: E402

import consumer  # noqa: E402
import peek  # noqa: E402
import producer  # noqa: E402
import setup_queues  # noqa: E402


@pytest.fixture
def sqs():
    with mock_aws():
        yield boto3.client("sqs", region_name="us-east-1")


def test_creare_inserare_citire_consumare(sqs):
    url, dlq_url = setup_queues.create_queues(sqs)
    for _ in range(3):
        producer.send_order(sqs, url, producer.comanda_noua())

    assert peek.count_messages(sqs, url)[0] == 3
    assert len(peek.peek(sqs, url)) == 3
    assert peek.count_messages(sqs, url)[0] == 3  # peek nu ascunde mesajele

    ok, fail, _ = consumer.poll_once(sqs, url, wait_seconds=0)
    assert (ok, fail) == (3, 0)
    assert peek.count_messages(sqs, url) == (0, 0)


def test_mesaj_invalid_ajunge_in_dlq(sqs):
    url, dlq_url = setup_queues.create_queues(sqs)
    producer.send_invalid(sqs, url)

    for _ in range(3):  # 3 incercari esuate
        ok, fail, _ = consumer.poll_once(sqs, url, wait_seconds=0)
        assert (ok, fail) == (0, 1)
        time.sleep(1.2)  # asteptam sa expire visibility timeout-ul

    consumer.poll_once(sqs, url, wait_seconds=0)  # a 4-a citire -> mutat in DLQ
    assert peek.count_messages(sqs, url) == (0, 0)
    dlq = peek.peek(sqs, dlq_url)
    assert [m["Body"] for m in dlq] == ["nu-e-json"]


@pytest.mark.parametrize("body", ['{"id":"a"}', '{"id":"a","produs":"x","cantitate":0}', "[1,2]"])
def test_validare(body):
    with pytest.raises(consumer.ComandaInvalida):
        consumer.proceseaza(body)
