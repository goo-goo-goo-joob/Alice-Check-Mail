import json
import random

from flask import Flask
from flask import request

from .handlers import *

app = Flask(__name__)

AGREE = ['Проверь почту', 'Хочу', 'Давай']


class UserRecord:
    def __init__(self, uid: str):
        self.uid = uid
        self.email = None
        self.token = None
        self.inbox = None


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
            "end_session": False,
            "text": ""
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


def main_handler(req, response):

    #TODO: Проверка на запрос выхода и помощи

    if 'state' not in req:
        start_handler(req, response)
        return

    curState = req['state']['session']['value']

    if curState == States.OneMAIL:
        return


def start_handler(req, response):

    # Проверка авторизованности пользователя
    if (random.random() > 0.7):
        #отправка сообщения об авторизации
        do_auth(req, response)
        return

    # Получение числа отправителей
    M = int(int(random.random() * 10) / 3)

    # Получение числа писем (общее)
    N = int(int(random.random() * 10) / 3) + M

    if N == 0:
        # Писем нет
        do_no_mails(req, response)
        return

    if N == 1 and M == 1:
        # 1 письмо
        name = "RandomName"
        topic = "RandomTopic"

        do_one_mail(req, response, name, topic)
        return

    if N > 1 and M == 1:
        # Несколько писем от 1 отправителя
        name = "RandomName"
        topics = []
        for i in range(N):
            topics.append('RandomTopic{}'.format(i+1))

        do_one_sender(req, response, name, topics)
        return

    if N > 1 and M > 1:
        # Несколько писем от нескольких отправителей
        names = []
        Ntopics = dict()
        for i in range(M):
            names.append('RandomName{}'.format(i+1))
            if i+1 == M:
                Ntopics['RandomName{}'.format(i+1)] = N - i
            else:
                Ntopics['RandomName{}'.format(i+1)] = 1

        do_many_senders(req, response, names ,Ntopics)
        return
    else:
        do_error(req, response)
        return






