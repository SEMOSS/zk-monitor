# ZooKeeper Monitor

A simple Streamlit app to monitor ZooKeeper.

## Installation
1. Create virtual environment & install the required packages
```bash
python3 -m venv venv
pip install -r requirements.txt
```
2. Create a `.env` file in the root directory and add the ip address and port of the ZooKeeper service
```bash
ZK_HOSTS="ip_address:port"
```

## Start the app
```bash
streamlit run app.py
```