# twitchbot

A Simple Suckless ChatBot for Twitch Streams

```bash
virtualenv -p python3 venv
pip install -r requirements.txt
cp example.ini config.ini
# Set Everything in [config] except oauth
nano config.ini
# Print OAuth Authentication URL
./chatbot -c config.ini -p
# Follow Printed Instructions
# Edit Config with [config] oauth set
nano config.ini
# Start your Bot
./chatbot -c config.ini
```
