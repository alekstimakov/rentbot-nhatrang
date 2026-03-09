# Deploy To Ubuntu Server

## 1. Upload project

From your local machine:

```bash
scp -r ./project ubuntu@<SERVER_IP>:/opt/tg-bot-rent
```

or with `rsync`:

```bash
rsync -avz --delete ./project/ ubuntu@<SERVER_IP>:/opt/tg-bot-rent/
```

## 2. Install Python and venv on server

```bash
ssh ubuntu@<SERVER_IP>
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

## 3. Install dependencies

```bash
cd /opt/tg-bot-rent
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 4. Configure environment

Create `/opt/tg-bot-rent/.env` (or update existing):

```env
BOT_TOKEN=...
ADMIN_IDS=123456789
ADMIN_PASSWORD=...
DB_PATH=data/bikes.db
```

## 5. Run bot manually (first check)

```bash
cd /opt/tg-bot-rent
source .venv/bin/activate
python main.py
```

If it starts correctly, stop it with `Ctrl+C`.

## 6. Enable auto-start with systemd

```bash
sudo cp deploy/tg-bot-rent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tg-bot-rent
sudo systemctl start tg-bot-rent
```

Check status/logs:

```bash
sudo systemctl status tg-bot-rent
sudo journalctl -u tg-bot-rent -f
```

## 7. Update release

After uploading new version:

```bash
cd /opt/tg-bot-rent
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart tg-bot-rent
```
