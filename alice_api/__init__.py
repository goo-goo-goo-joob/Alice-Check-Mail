import json
import random

from enum import Enum, auto
from flask import Flask
from flask import request



app = Flask(__name__)

AGREE = ['Проверь почту', 'Хочу', 'Давай']
DISAGREE = ['нет']


class States(Enum):
    START = auto()
    CHECK = auto()
    AUTH = auto()  # 0
    NoMAILS = auto()  # 1
    OneMAIL = auto()  # 2
    OneSENDER = auto()  # 3
    ManySENDERS = auto()  # 4
    SmallMAIL = auto()  # 5
    LargeMAIL = auto()  # 6
    ContMAIL = auto()  # 9
    NoMoreMAIL = auto()  # 7
    AnyMoreMAIL = auto()  # 8
    AnyHELP = auto()  # 10


class UserRecord:
    def __init__(self, uid: str):
        self.uid = uid
        self.email = None
        self.token = None
        self.inbox = None
        self.state = None


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


def main_handler(req, res):

    #TODO: Проверка на запрос выхода и помощи

    if 'state' not in req:
        start_handler(req, res)
        return

    curState = req['state']['session']['value']

    if curState == States.AUTH:
        start_handler(req, res)
        return

    if curState == States.OneMAIL:
        if 'request' in req and 'original_utterance' in req['request'] and req['request']['original_utterance'] in AGREE:
            read_message(req, res)
            return

        if 'request' in req and 'original_utterance' in req['request'] and req['request']['original_utterance'] in DISAGREE:
            do_any_help(req, res)
            return

        do_not_understand(req, res)

    if curState == States.OneSENDER:

        if 'request' in req and 'nlu' in req['request'] and 'tokens' in req['request']['nlu']:
            numMessge = req['request']['nlu']['tokens'][0]

            do_one_mail(req, res)
            return

        do_not_understand(req, res)

    if curState == States.ManySENDERS:

        if 'request' in req and 'nlu' in req['request'] and 'tokens' in req['request']['nlu']:
            numMessge = req['request']['nlu']['tokens'][0]

            do_one_mail(req, res)
            return


def start_handler(req, res):

    # Проверка авторизованности пользователя
    if (random.random() > 0.7):
        #отправка сообщения об авторизации
        do_auth(req, res)
        return

    # Получение числа отправителей
    M = int(int(random.random() * 10) / 3)

    # Получение числа писем (общее)
    N = int(int(random.random() * 10) / 3) + M

    if N == 0:
        # Писем нет
        do_no_mails(req, res)
        do_any_help(req, res)
        return

    if N == 1 and M == 1:
        # 1 письмо
        do_one_mail(req, res)
        return

    if N > 1 and M == 1:
        # Несколько писем от 1 отправителя
        do_one_sender(req, res)
        return

    if N > 1 and M > 1:
        # Несколько писем от нескольких отправителей
        do_many_senders(req, res)
        return
    else:
        do_error(req, res)
        return


def read_message(req, res):

    #TODO: content - содержание письма
    content = 'Состояние сессии перестанет храниться, если в ответе навыка не вернуть свойство session_state. Поэтому если для конкретного запроса состояние не меняется, но его нужно продолжать хранить, навыку следует вернуть тот же объект session_state, что пришел в запросе.'
    name = 'RandomName'

    if len(content.split()) > 30:
        content = ' '.join(content.split()[:20])
        do_large_mail(req, res, name, content)
    else:
        do_small_mail(req, res, name, content)


def do_error(req, res):
    text = 'Error!!! '
    res['response']['text'] += text


def do_not_understand(req, res):
    text = 'Я вас не понимаю, повторите '
    res['response']['text'] += text
    temp_state = States.AUTH
    if 'state' in req and 'session' in req['state'] and 'value' in req['state']['session']:
        temp_state = req['state']['session']['value']
    res['user_state_update'] = temp_state


def do_auth(req, res):
    text = 'Я могу проверить вашу почту, просто скажите мне об этом. '
    res['response']['text'] += text
    res['user_state_update'] = States.AUTH
    if 'access_token' not in req['session']['user']:
        res['start_account_linking'] = {}


def do_no_mails(req, res):
    # У вас нет новых писем

    text = 'У вас нет новых писем. '
    res['response']['text'] += text
    res['user_state_update'] = States.NoMAILS


def do_one_mail(req, res):
    # У вас 1 новое письмо от Имя с темой тема. Вам прочитать это письмо?
    name = "RandomName"
    topic = "RandomTopic"

    text = 'У вас 1 новое письмо от {0} с темой {1}. Вам прочитать это письмо? '.format(name, topic)
    res['response']['text'] += text
    res['user_state_update'] = States.OneMAIL


def do_one_sender(req, res):
    # От имя пришло n1 писем с темами: 1. тема1 2. тема2. Назовите номер письма, содержание которого хотите прослушать
    # TODO: числительные
    N = 3
    name = "RandomName"
    topics = []
    for i in range(N):
        topics.append('RandomTopic{}'.format(i+1))

    text = 'От {0} пришло {1} писем с темами: '.format(name, len(topics))
    for i in range(len(topics)):
        text += '{0}. {1} '.format(i + 1, topics[i])
    text += 'Назовите номер письма, содержание которого хотите прослушать. '
    res['response']['text'] += text
    res['user_state_update'] = States.OneSENDER


def do_many_senders(req, res):
    # У вас: 1. n1 писем от Имя1 2. n2 писем от Имя2. Темы какого отправителя вы хотите прослушать? Можно назвать порядковый номер отправителя
    # TODO: числительные
    N = 5
    M = 3
    names = []
    Ntopics = dict()
    for i in range(M):
        names.append('RandomName{}'.format(i+1))
        if i+1 == M:
            Ntopics['RandomName{}'.format(i+1)] = N - i
        else:
            Ntopics['RandomName{}'.format(i+1)] = 1

    text = "У вас: "
    for i, name in enumerate(names):
        text += '{0}. {1} писем от {2}.'.format(i + 1, Ntopics[name], name)
    text += 'Темы какого отправителя вы хотите прослушать? Можно назвать порядковый номер отправителя. '
    res['response']['text'] += text
    res['user_state_update'] = States.ManySENDERS


def do_small_mail(req, res, name, content):
    # Письмо от Имя: (содержание)

    text = 'Письмо от {0}: {1}'.format(name, content)
    res['response']['text'] += text
    res['user_state_update'] = States.SmallMAIL


def do_large_mail(req, res, name, content):
    # Письмо от Имя: (содержание первые 20 слов). Это были первые 20 слов, дальше продолжать?
    # TODO: числительные

    text = 'Письмо от {}: {}. Это были первые 20 слов, дальше продолжать?'.format(name, content)
    res['response']['text'] += text
    res['user_state_update'] = States.LargeMAIL


def do_cont_mail(req, res, name, content):
    # Продолжение письма от имя: (продолжение)

    text = 'Продолжение письма от {0}: {1}'.format(name, content)
    res['response']['text'] += text
    res['user_state_update'] = States.ContMAIL


def do_no_more_mails(req, res):
    # У вас больше нет новых сообщений

    text = 'У вас больше нет новых сообщений. '
    res['response']['text'] += text
    res['user_state_update'] = States.NoMoreMAIL


def do_any_more_mails(req, res):
    # У вас еще есть непрочитанные сообщения, вы хотите их прослушать?

    text = 'У вас еще есть непрочитанные сообщения, вы хотите их прослушать? '
    res['response']['text'] += text
    res['user_state_update'] = States.AnyMoreMAIL


def do_any_help(req, res):
    # Я могу вам еще чем-то помочь? Проверить вашу почту еще раз?

    text = 'Я могу вам еще чем-то помочь? Проверить вашу почту еще раз? '
    res['response']['text'] += text
    res['user_state_update'] = States.AnyHELP







