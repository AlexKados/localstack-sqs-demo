# localstack-sqs-demo

Prototip funcțional pentru **Amazon SQS** (Simple Queue Service) rulat local cu **LocalStack**.
Proiect realizat ca parte practică a referatului *„Arhitecturi Cloud cu Amazon Web Services. Privire de ansamblu și validare practică prin LocalStack”*.

## Ce demonstrează

Un magazin online primește comenzi. În loc ca serverul care primește comanda să o proceseze imediat, o pune într-o **coadă SQS**. Un **consumator** separat ia comenzile din coadă în ritmul lui, le procesează și le șterge. Comenzile care nu pot fi procesate (de exemplu, un mesaj care nu este JSON) sunt reîncercate de 3 ori, apoi SQS le mută automat într-o **dead-letter queue (DLQ)**.

```
 producer.py ──send_message──▶ [ comenzi ] ──receive/delete──▶ consumer.py
                                    │
                    după 3 citiri eșuate (RedrivePolicy)
                                    ▼
                             [ comenzi-dlq ]  ◀── peek.py --dlq
```

| Operația     | Script Python               | Comanda AWS CLI echivalentă                 |
|--------------|-----------------------------|---------------------------------------------|
| Creare       | `src/setup_queues.py`       | `aws sqs create-queue`                      |
| Inserare     | `src/producer.py`           | `aws sqs send-message`                      |
| Citire       | `src/peek.py`               | `aws sqs receive-message --visibility-timeout 0` |
| Consumare    | `src/consumer.py`           | `aws sqs receive-message` + `delete-message`|
| Ștergere     | `src/cleanup.py`            | `aws sqs purge-queue` / `delete-queue`      |

## Structura proiectului

```
localstack-sqs-demo/
├── docker-compose.yml        # LocalStack (metoda B)
├── .env.localstack.example   # model pentru token-ul LocalStack
├── requirements.txt          # boto3
├── requirements-dev.txt      # + pytest, moto (pentru teste)
├── src/
│   ├── config.py             # clientul SQS, endpoint, numele cozilor
│   ├── setup_queues.py       # CREARE coadă + DLQ
│   ├── producer.py           # INSERARE comenzi
│   ├── peek.py               # CITIRE fără efecte
│   ├── consumer.py           # CONSUMARE + ȘTERGERE mesaje procesate
│   └── cleanup.py            # golire / ștergere cozi
└── tests/test_flow.py        # teste automate ale fluxului
```

---

## 1. Instalarea uneltelor

Aveți nevoie de: **Git, Docker Desktop, Python 3.10+, AWS CLI v2** și, pentru metoda A, **lstk**.

**Windows** (cmd; primul pas ca administrator, apoi restart):
```bat
wsl --install
winget install --id Git.Git -e
winget install --id Docker.DockerDesktop -e
winget install --id Python.Python.3.12 -e
winget install --id Amazon.AWSCLI -e
winget install --id OpenJS.NodeJS.LTS -e
:: terminal nou, apoi (doar metoda A):
npm install -g @localstack/lstk
```

**macOS** (Terminal, cu Homebrew):
```bash
brew install git python awscli
brew install --cask docker
open -a Docker
brew install localstack/tap/lstk     # doar metoda A
```

Verificare (fiecare comandă trebuie să afișeze o versiune):
```bash
git --version
docker --version
python --version        # pe macOS: python3 --version
aws --version
lstk --version          # doar metoda A
```

Creați un cont gratuit pe **app.localstack.cloud** (planul Hobby e suficient: SQS este inclus).

## 2. Descărcarea proiectului și a dependențelor

```bash
git clone https://github.com/AlexKados/localstack-sqs-demo.git
cd localstack-sqs-demo
python -m venv .venv
```
Activarea mediului virtual:
- Windows: `.venv\Scripts\activate`
- macOS: `source .venv/bin/activate`

```bash
pip install -r requirements.txt
```

## 3. Pornirea LocalStack — alegeți **o singură** metodă

> ⚠️ Nu porniți ambele metode simultan: amândouă folosesc portul 4566. Înainte de a schimba metoda, opriți-o pe cea veche (`lstk stop` sau `docker compose stop`).

### Metoda A — `lstk` (recomandată)
```bash
lstk            # prima dată: login în browser, apoi pornește LocalStack
lstk status     # trebuie să afișeze „LocalStack AWS Emulator is running”
```

### Metoda B — `docker compose`
```bash
# Windows:
copy .env.localstack.example .env.localstack
# macOS:
cp .env.localstack.example .env.localstack
```
Editați `.env.localstack` și puneți token-ul din pagina *Auth Tokens* (începe cu `ls-`). Fișierul este în `.gitignore`, nu se comite.
```bash
docker compose up -d
curl http://localhost:4566/_localstack/health     # "sqs": "available"
```

## 4. Configurarea terminalului

Scripturile Python trimit cererile către `http://localhost.localstack.cloud:4566`, cu credențialele `test/test`, regiunea `us-east-1` — **nu este nevoie să setați nimic**. Pentru comenzile `aws` (metoda B) setați:

**Windows (cmd)**
```bat
set AWS_ENDPOINT_URL=http://localhost.localstack.cloud:4566
set AWS_ACCESS_KEY_ID=test
set AWS_SECRET_ACCESS_KEY=test
set AWS_DEFAULT_REGION=us-east-1
```
**macOS**
```bash
export AWS_ENDPOINT_URL=http://localhost.localstack.cloud:4566
export AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=us-east-1
```
Verificare: `aws sts get-caller-identity` trebuie să arate contul **000000000000** (deci comenzile ajung la LocalStack, nu la AWS-ul real). În metoda A puteți folosi direct `lstk aws ...` în loc de `aws ...`.

## 5. Utilizare — scenariul complet

> Pe macOS folosiți `python3` dacă nu sunteți într-un mediu virtual.

**5.1 Creare** — coada `comenzi` + dead-letter queue `comenzi-dlq` (după 3 citiri eșuate, timeout de vizibilitate 5 s):
```bash
python src/setup_queues.py
```
```
Coada principala : http://sqs.us-east-1.localhost.localstack.cloud:4566/000000000000/comenzi
Dead-letter queue: http://sqs.us-east-1.localhost.localstack.cloud:4566/000000000000/comenzi-dlq
```

**5.2 Inserare** — trei comenzi valide și una invalidă:
```bash
python src/producer.py
python src/producer.py --invalid
```
```
Trimis {'id': '692ae34c', 'produs': 'monitor', 'cantitate': 1, ...}  MessageId=7f2429a0-...
...
Trimis mesaj INVALID, MessageId=04d82ca7-...
```

**5.3 Citire fără efecte** — numărul de mesaje și conținutul lor; mesajele rămân în coadă:
```bash
python src/peek.py
```
```
Coada 'comenzi': 4 mesaje vizibile, 0 in procesare
  - 7f2429a0-...  (citit de 1 ori)  {"id": "692ae34c", "produs": "monitor", ...}
  - 04d82ca7-...  (citit de 1 ori)  nu-e-json
```
> Notă: și o citire „fără efecte” crește contorul de citiri al mesajului (`ApproximateReceiveCount`), deci contează la `maxReceiveCount`.

**5.4 Consumare** — consumatorul procesează și șterge comenzile valide; mesajul invalid nu se șterge:
```bash
python src/consumer.py
```
```
  [OK] comanda 692ae34c: 1 x monitor -> procesata si stearsa
  [OK] comanda 91b9dc76: 1 x monitor -> procesata si stearsa
  [OK] comanda 4b74ef23: 1 x casti -> procesata si stearsa
  [EROARE, incercarea 2] nu este JSON: 'nu-e-json' -> mesajul NU se sterge
  [EROARE, incercarea 3] nu este JSON: 'nu-e-json' -> mesajul NU se sterge
Gata: 3 procesate, 2 esuari
```
Consumatorul se oprește după 3 citiri goale la rând; cu `--forever` ascultă continuu (Ctrl+C pentru oprire).

**5.5 Dead-letter queue** — la a 4-a citire (peek + 2 încercări ale consumatorului + încă una), SQS nu mai livrează mesajul invalid, ci îl mută singur în DLQ. Consumatorul de la 5.4 face asta deja în ~10 secunde; verificați:
```bash
python src/peek.py          # coada principală: 0 mesaje
python src/peek.py --dlq    # comenzi-dlq: 1 mesaj
```
```
Coada 'comenzi-dlq': 1 mesaje vizibile, 0 in procesare
  - 04d82ca7-...  (citit de 4 ori)  nu-e-json
```

**5.6 Ștergere**
```bash
python src/cleanup.py --purge    # golește ambele cozi
python src/cleanup.py            # șterge ambele cozi
```

## 6. Aceleași operații doar cu AWS CLI

Exemplele sunt pentru macOS; în cmd, `$Q` devine `%Q%`, `\` de la final de rând devine `^`, iar JSON-ul se scrie `"{\"id\":\"c1\"}"`. În metoda A, puneți `lstk` în fața fiecărei comenzi `aws`.

```bash
# creare
aws sqs create-queue --queue-name comenzi
Q=$(aws sqs get-queue-url --queue-name comenzi --query QueueUrl --output text)
#   Windows: set Q=http://sqs.us-east-1.localhost.localstack.cloud:4566/000000000000/comenzi

# inserare
aws sqs send-message --queue-url "$Q" \
  --message-body '{"id":"c1","produs":"laptop","cantitate":1}'

# câte mesaje sunt
aws sqs get-queue-attributes --queue-url "$Q" --attribute-names ApproximateNumberOfMessages

# citire fără a ascunde mesajele
aws sqs receive-message --queue-url "$Q" --max-number-of-messages 10 --visibility-timeout 0

# consumare: citire + ștergere cu receipt handle
RH=$(aws sqs receive-message --queue-url "$Q" --query "Messages[0].ReceiptHandle" --output text)
aws sqs delete-message --queue-url "$Q" --receipt-handle "$RH"

# golire / ștergere coadă
aws sqs purge-queue --queue-url "$Q"
aws sqs delete-queue --queue-url "$Q"
```
Endpoint specific LocalStack care arată toate mesajele fără să le modifice:
```bash
curl "http://localhost.localstack.cloud:4566/_aws/sqs/messages?QueueUrl=$Q"
```

## 7. Teste automate

Testele rulează pe un SQS simulat în memorie (biblioteca `moto`), deci nu au nevoie de LocalStack pornit:
```bash
pip install -r requirements-dev.txt
pytest -v
```
Verifică: crearea cozilor, inserarea, citirea fără efecte, consumarea și ștergerea, validarea comenzilor și mutarea mesajului invalid în DLQ după 3 încercări.

## 8. Oprire

```bash
lstk stop                 # metoda A
docker compose stop       # metoda B
```
Pe planul Hobby starea este în memorie: la repornire cozile nu mai există — rulați din nou `python src/setup_queues.py`.

## 9. Probleme frecvente

| Simptom | Cauză / soluție |
|---|---|
| `Could not connect to the endpoint URL` | LocalStack nu rulează: `lstk status` sau `docker compose ps`. |
| `QueueDoesNotExist` | LocalStack a fost repornit: rulați `python src/setup_queues.py`. |
| `port is already allocated` | Rulează deja un LocalStack (altă metodă): `lstk stop` / `docker compose stop`. |
| LocalStack se oprește imediat (metoda B) | Lipsește token-ul din `.env.localstack`: `docker compose logs localstack`. |
| `aws sts get-caller-identity` arată alt cont | Comenzile merg la AWS-ul real! Setați `AWS_ENDPOINT_URL` (secțiunea 4). |

## Configurare

Toate valorile se pot schimba prin variabile de mediu, fără a modifica codul:

| Variabila | Implicit | Rol |
|---|---|---|
| `AWS_ENDPOINT_URL` | `http://localhost.localstack.cloud:4566` | unde merg cererile |
| `QUEUE_NAME` / `DLQ_NAME` | `comenzi` / `comenzi-dlq` | numele cozilor |
| `MAX_RECEIVE_COUNT` | `3` | după câte citiri eșuate mesajul ajunge în DLQ |
| `VISIBILITY_TIMEOUT` | `5` | câte secunde un mesaj citit rămâne ascuns |

## Bibliografie

- LocalStack — documentație: https://docs.localstack.cloud
- Amazon SQS — Developer Guide: https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/
- Boto3 — SQS client: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sqs.html
