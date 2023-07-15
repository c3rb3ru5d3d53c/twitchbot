#!/usr/bin/env python

import sys
import socket
import requests
from urllib.parse import quote
from argparse import ArgumentParser
from configparser import ConfigParser

__author__  = '@c3rb3ru5d3d53c'
__version__ = '1.0.0'

def print_oauth_url(client_id, redirect_uri='https://localhost', scope='chat:edit chat:read moderation:read openid'):
    url = 'https://id.twitch.tv/oauth2/authorize?'
    url += 'response_type=token'
    url += f'&client_id={client_id}'
    url += f'&redirect_uri={quote(redirect_uri)}'
    url += f'&scope={quote(scope)}'
    print(f'Visit: {url}')
    print('1. Allow Access')
    print('2. Copy OAuth access_token From Redirect URL')

class TwitchBot():
    def __init__(self, username, channel):
        self.username = username
        self.channel = '#' + channel

    def set_config(self, config):
        self.cfg = config

    def api_connect(self, client_id, client_secret, oauth):
        self.oauth = oauth
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = self.api_get_access_token()
        assert self.access_token is not None
        self.user_id = self.api_get_user()['data'][0]['id']
        assert self.user_id is not None
        print(self.api_get_moderators())

    def irc_connect(self, oauth):
        self.oauth = oauth
        self.sock = socket.socket()
        self.sock.connect(('irc.chat.twitch.tv', 6667))
        self.sock.send(f"PASS oauth:{self.oauth}\r\n".encode())
        self.sock.send(f"NICK {self.username}\r\n".encode())
        self.sock.send(f"JOIN {self.channel}\r\n".encode())
    
    def irc_listen(self, callback):
        while True:
            messages = [' '.join(m.decode('utf-8').split(' ')[1:]) for m in self.sock.recv(512).split(b'\r\n') if m.decode('utf-8').startswith(':')]
            for message in messages:
                if message.startswith('PING'):
                    self.irc_pong()
                    continue
                callback(self, message)

    def irc_pong(self):
        self.sock.send("PONG\r\n".encode())

    def disconnect(self):
        self.sock.close()

    def api_get_access_token(self):
        r = requests.post(
            url='https://id.twitch.tv/oauth2/token',
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            data=f'client_id={self.client_id}&client_secret={self.client_secret}&grant_type=client_credentials'
        )
        if r.status_code != 200: return None
        return r.json()['access_token']

    def api_get_user(self):
        r = requests.get(
            url=f'https://api.twitch.tv/helix/users?login={self.username}',
            headers={
                'Authorization': f'Bearer {self.access_token}',
                'Client-Id': f'{self.client_id}'
            }
        )
        if r.status_code != 200: return None
        if len(r.json()['data']) <= 0: return None
        return r.json()

    def api_get_moderators(self):
        r = requests.get(
            url=f'https://api.twitch.tv/helix/moderation/moderators?broadcaster_id={self.user_id}',
            headers={
                'Authorization': f'Bearer {self.oauth}',
                'Client-Id': f'{self.client_id}'
            }
        )
        if r.status_code != 200: return None
        return r.json()

    @staticmethod
    def irc_get_message(message):
        if message.startswith('PRIVMSG') is False: return None
        return ' '.join(message.split(' ')[2:]).lstrip(':')

    @staticmethod
    def irc_get_command(message):
        if message.startswith('PRIVMSG') is False: return None
        message = ' '.join(message.split(' ')[2:]).lstrip(':')
        if message.startswith('!') is False: return None
        return message.lstrip('!').split(' ')

    def irc_send_message(self, message, debug=False):
        data = f"PRIVMSG {self.channel} :{message}\r\n".encode()
        if debug is True: print(data.rstrip(b'\r\n').decode('utf-8'))
        self.sock.send(data)

def callback(session, message):
    print(message)
    command = session.irc_get_command(message)
    if command is None: return None
    if command[0] == 'help':
        if len(command) > 1:
            for section in session.cfg.sections():
                for k,v in session.cfg[section].items():
                    if command[1] == section and k == 'help': session.irc_send_message(v, debug=True)
        if len(command) == 1:
            m = 'commands: '
            for section in session.cfg.sections():
                for k,v in session.cfg[section].items():
                    if k == 'help': m += '!' + section + ' '
            if len(m) > 0: session.irc_send_message(m.rstrip(' '), debug=True)
    if command[0] == 'whoami' and command[0] in session.cfg.sections():
        session.irc_send_message(session.api_get_user()['data'][0]['description'])
    if command[0] in session.cfg.sections():
        if 'message' in session.cfg[command[0]]:
            session.irc_send_message(session.cfg[command[0]]['message'], debug=True)
            return None

def main():
    try:
        p = ArgumentParser(
            prog=f'twitchbot v{__version__}',
            description='A Twitch Chatbot',
            epilog=f'Author: {__author__}'
        )
        p.add_argument(
            '--version',
            action='version',
            version=f'v{__version__}'
        )
        p.add_argument(
            '-c',
            '--config',
            type=str,
            default=None,
            help='Config File',
            required=True
        )
        p.add_argument(
            '-p',
            '--print-oauth-url',
            action='store_true',
            default=False,
            help='Print OAuth URL'
        )
        args = p.parse_args()
        
        cfg = ConfigParser()
        cfg.read(args.config)
        if args.print_oauth_url:
            print_oauth_url(
                client_id=cfg['config']['client_id'],
                redirect_uri=cfg['config']['redirect_uri'],
                scope=cfg['config']['scope']
            )
            sys.exit(0)
        bot = TwitchBot(
            cfg['config']['username'],
            cfg['config']['channel'])
        bot.api_connect(
            cfg['config']['client_id'],
            cfg['config']['client_secret'],
            cfg['config']['oauth'])
        bot.irc_connect(cfg['config']['oauth'])
        bot.set_config(cfg)
        bot.irc_listen(callback)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
