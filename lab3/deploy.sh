#!/bin/bash
# Last deployment commands expecting to be run inside the folder where chatbot.py lives

# Log the content both on NTFY and a temp file
function log() {
    echo "$1" >>/tmp/chatbotlog.txt
    curl -d "$1" ntfy.sh/superchatbot
}

log "starting running the deploy.sh"

sudo apt update
sudo apt install -y git python3-pip tree

log "python pip installed $(python -V) and $(pip -V)"

log "repos cloned $(pwd) and\\n $(ls)"
log "Tree view $(tree)"
log "Installing pip dependencies"
pip install -r requirements.txt

pkill streamlit # kill previous streamlit processes

export PATH=$PATH:$HOME/.local/bin
# Run the bot in background
log "Launching the bot !"
nohup streamlit run chatbot.py &>/tmp/chatbotlog.txt &
