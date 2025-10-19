#!/bin/bash

# Log the content both on NTFY and a temp file
function log() {
    echo "$1" >>/tmp/chatbotlog.txt
    curl -d "$1" ntfy.sh/superchatbot
}

log "starting running the init.sh"
apt update
apt install -y git python-pip

log "python pip installed $(python -V) and $(pip -V)"

mkdir /deploy
cd /deploy
git clone https://github.com/samuelroland/CloudSys-labs.git labs || log "failed to git clone"
cd labs/lab3

log "repos cloned $(pwd) and\\n $(ls)"
log "Tree view $(tree)"
log "Installing pip dependencies"
pip install -r requirements.txt
log "All good, starting streamlit chatbot !"
streamlit run chatbot.py
