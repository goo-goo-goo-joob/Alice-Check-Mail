from flask import Flask
from flask import request
import json
from enum import Enum, auto
import random

app = Flask(__name__)

AGREE = ['Проверь почту', 'Хочу', 'Давай']


class UserRecord:
    def __init__(self, uid: str):
        self.uid = uid
        self.email = None
        self.token = None
        self.inbox = None
        self.state = States.START


class SessionStorage:
    def __init__(self):
        self.storage = {}

    def get(self, uid: str) -> UserRecord:
        if uid not in self.storage:
            self.storage[uid] = UserRecord(uid)
        return self.storage[uid]

    def add(self, user: UserRecord):
        assert isinstance(user, UserRecord)
        if user.uid not in self.storage:
            self.storage[user.uid] = user

    def delete(self, uid: str):
        if uid not in self.storage:
            del self.storage[uid]


storage = SessionStorage()


class States(Enum):
    START = auto()
    CHECK = auto()


def handler_start(req, res):
    text = 'Я могу проверить вашу почту, просто скажите мне об этом.'
    res['response']['text'] = text
    storage.get(req['session']['user_id']).state = States.START


def choose_start(req, res):
    if 'request' in req and 'original_utterance' in req['request'] and req['request']['original_utterance'] in AGREE:
        return handler_check(req, res)
    return handler_start(req, res)


def handler_check(req, res):
    text = 'Проверила вашу почту. У вас 2 новых сообщения. Хотите прочитаю?'
    res['response']['text'] = text
    storage.get(req['session']['user_id']).state = States.CHECK


def choose_check(req, res):
    if 'request' in req and 'original_utterance' in req['request'] and req['request']['original_utterance'] in AGREE:
        return handler_read(req, res)
    return handler_start(req, res)


def handler_read(req, res):
    text = 'Учебный офис. Срочно! Важно! Арен Маркосян, Вас отчислили. Сорян.'
    if random.random() > 0.5:
        text += 'Хотите услышать следующее сообщение?'
        storage.get(req['session']['user_id']).state = States.CHECK
    else:
        text += 'Больше нет новых сообщений.'
        storage.get(req['session']['user_id']).state = States.START
    res['response']['text'] = text


finite_state_machine = {
    States.START: choose_start,
    States.CHECK: choose_check,
}


@app.route('/', methods=['POST'])
def main():
    response = {
        "version": request.json['version'],
        "session": request.json['session'],
        "response": {
            "end_session": False
        }
    }
    user = storage.get(request.json['session']['user_id'])
    if user.state == States.START:
        choose_start(request.json, response)
    elif user.state == States.CHECK:
        choose_check(request.json, response)
    else:
        choose_start(request.json, response)

    return json.dumps(
        response,
        ensure_ascii=False,
        indent=2
    )

