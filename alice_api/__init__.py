import datetime
import json
import traceback

from flask import Flask
from flask import request

from alice_api.mail import YandexIMAP, ReadException, ImapException
from alice_api.passport import get_user_email

app = Flask(__name__)

AGREE = ['хочу', 'давай', 'да', 'ну давай', 'ну хочу', 'ну да']
DISAGREE = ['нет', 'не хочу', 'не надо']
RELOAD = ['обновить', 'проверить почту', 'обнови', 'проверь почту', 'обновите', 'проверьте почту', 'проверь', 'проверить', 'проверьте']
HELP = ['помощь', 'справка']
EXIT = ['выход', 'хватит']


class BadMessageException(Exception):
    pass


class States():
    START = 11
    CHECK = 12
    AUTH = 0  # 0
    NoMAILS = 1  # 1
    OneMAIL = 2  # 2
    OneSENDER = 3  # 3
    ManySENDERS = 4  # 4
    SmallMAIL = 5  # 5
    LargeMAIL = 6  # 6
    ContMAIL = 9  # 9
    NoMoreMAIL = 7  # 7
    AnyMoreMAIL = 8  # 8
    AnyHELP = 10  # 10


class UserRecord:
    def __init__(self, uid: str):
        self.uid = uid
        self.email = None
        self.token = None
        self.inbox = None
        self.state = None
        self.inbox_date = None
        self.num_letter = None
        self.num_sender = None
        self.senders = None
        self.last_said = None

    @property
    def is_auth(self):
        """
        Проверка авторизации пользователя
        """
        return self.token is not None

    def _check_passport(self):
        if self.email is None:
            self.email = get_user_email(self.token)

    def _check_mail(self):
        self._check_passport()
        imap = YandexIMAP()
        imap.xoauth2(self.email, self.token)
        self.inbox = imap.get_all_mail()
        self.inbox_date = datetime.datetime.now()
        imap.close()

    @property
    def get_senders(self):
        """
        Проверяет (обновляет) почту и получает всех отправителей с количеством писем от них
        """
        self._check_mail()
        senders = {}
        for unit_mail in self.inbox:
            if unit_mail['from'] not in senders:
                senders[unit_mail['from']] = 1
            else:
                senders[unit_mail['from']] += 1
        self.senders = list(senders.keys())
        return senders

    @property
    def get_count_mail(self):
        """
        Получает число всех писем
        """
        return len(self.inbox)

    def get_mail_from(self, sender, number):
        """
        Получает письмо (отправитель, тема, текст) с заданным номером от заданного номера отправителя
        """
        i = 0
        for unit_mail in self.inbox:
            if unit_mail['from'] == self.senders[sender]:
                if i == number:
                    return unit_mail
                i += 1
        raise BadMessageException('Простите, не могу прочитать это письмо.')

    def del_mail(self, sender, number):
        i = 0
        for j, unit_mail in enumerate(self.inbox):
            if unit_mail['from'] == self.senders[sender]:
                i += 1
                if i == number:
                    del self.inbox[j]
                    return

    def get_sender_topics(self, sender):
        topics = []
        for unit_mail in self.inbox:
            if unit_mail['from'] == self.senders[sender]:
                topics.append(unit_mail['subject'])
        return topics


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


# def handler_start(req, res):
#     text = 'Я могу проверить вашу почту, просто скажите мне об этом.'
#     res['response']['text'] = text
#     storage.get(req['session']['user_id']).state = States.START
#
#
# def choose_start(req, res):
#     if 'request' in req and 'original_utterance' in req['request'] and req['request']['original_utterance'].lower() in AGREE:
#         return handler_check(req, res)
#     return handler_start(req, res)
#
#
# def handler_check(req, res):
#     text = 'Проверила вашу почту. У вас 2 новых сообщения. Хотите прочитаю?'
#     res['response']['text'] = text
#
#
# def choose_check(req, res):
#     if 'request' in req and 'original_utterance' in req['request'] and req['request']['original_utterance'].lower() in AGREE:
#         return handler_read(req, res)
#     return handler_start(req, res)
#
#
# def handler_read(req, res):
#     text = 'Учебный офис. Срочно! Важно! Арен Маркосян, Вас отчислили. Сорян.'
#     if random.random() > 0.5:
#         text += 'Хотите услышать следующее сообщение?'
#         storage.get(req['session']['user_id']).state = States.CHECK
#     else:
#         text += 'Больше нет новых сообщений.'
#         storage.get(req['session']['user_id']).state = States.START
#     res['response']['text'] = text


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
    try:
        main_handler(request.json, response)
    except ImapException:
        response['response']['text'] = 'Не удалось авторизоваться в почте. ' \
                                       'Проверьте доступ по протоколу IMAP ' \
                                       'https://mail.yandex.ru/#setup/client'
        response['response']['tts'] = 'Не удалось авторизоваться в почте. ' \
                                      'Проверьте доступ по протоколу ИМАП ' \
                                      'мэйл точка яндекс точка ру слэш хэш сетап слэш клиент'
        # noinspection PyTypeChecker
        response['response']['buttons'] = [{
            "title": "Включить IMAP",
            "payload": {},
            "url": "https://mail.yandex.ru/#setup/client",
            "hide": True}]
        # noinspection PyTypeChecker
        response['response']['card'] = {"type": "BigImage",
                                        "image_id": "1652229/afa511d76876b7288ed5",
                                        "title": "Включить IMAP",
                                        "description": "Описание включения IMAP.",
                                        "button": response['response']['buttons']
                                        },
    except BadMessageException:
        response['response']['text'] = 'Не удалось воспроизвести письмо\n{}'.format(traceback.format_exc())
    except ReadException:
        response['response']['text'] = 'Не удалось прочитать письма\n{}'.format(traceback.format_exc())
    except Exception:
        response['response']['text'] = 'Неизвестная ошибка\n{}'.format(traceback.format_exc())

    response['response']['text'] = response['response']['text'][:1023]

    user = storage.get(request.json['session']['user_id'])
    user.last_said = response['response']['text']

    return json.dumps(
        response,
        ensure_ascii=False,
        indent=2
    )


def main_handler(req, res):
    user = storage.get(req['session']['user_id'])
    if 'user' not in req['session']:
        res['response']['text'] = 'Пожалуйста, войдите в аккаунт'
    if 'access_token' in req['session']['user']:
        user.token = req['session']['user']['access_token']
    else:
        user.token = None

    req['userRecord'] = user

    if 'original_utterance' in req['request']:
        req['request']['original_utterance'] = req['request']['original_utterance'].lower()

    if check_intent(req, 'YANDEX.HELP'):
        do_help(req, res)
        return

    if check_intent(req, 'exit'):
        do_exit(req, res)
        return

    if check_intent(req, 'YANDEX.REPEAT'):
        do_repeat(req, res)
        return

    if not user.is_auth:
        do_auth(req, res)
        return

    if check_intent(req, 'reload'):
        start_handler(req, res)
        return

    curState = 0
    if 'state' in req and 'session' in req['state'] and 'value' in req['state']['session']:
        curState = req['state']['session']['value']
    else:
        start_handler(req, res)
        return

    if curState == States.AUTH:
        start_handler(req, res)
        return

    if curState == States.OneMAIL:
        if check_intent(req, 'YANDEX.CONFIRM'):
            prep_read_message(req, res)
            return

        if check_intent(req, 'YANDEX.REJECT'):
            do_any_help(req, res)
            return

        do_not_understand(req, res)
        return

    if curState == States.OneSENDER:

        numMessge = get_number(req)
        if numMessge:
            user.num_letter = numMessge - 1
            user.num_sender = 0
            prep_read_message(req, res)
            return

        do_not_understand(req, res)
        return

    if curState == States.ManySENDERS:

        numSender = get_number(req)
        user.num_sender = numSender - 1
        num_mails = list(user.get_senders.values())[user.num_sender]

        if num_mails == 1:
            user.num_letter = 0
            prep_read_message(req, res)
            return

        if numSender:
            do_one_sender(req, res)
            return

        do_not_understand(req, res)
        return

    if curState == States.LargeMAIL:

        if check_intent(req, 'YANDEX.CONFIRM'):
            prep_read_message(req, res, cont=True)
            return

        if check_intent(req, 'YANDEX.REJECT'):
            other_mails(req, res)
            return

        do_not_understand(req, res)
        return

    if curState == States.AnyMoreMAIL:
        if check_intent(req, 'YANDEX.CONFIRM'):
            start_handler(req, res)
            return

        if check_intent(req, 'YANDEX.REJECT'):
            do_any_help(req, res)
            return

        do_not_understand(req, res)
        return

    if curState == States.AnyHELP:
        if check_intent(req, 'YANDEX.CONFIRM'):
            start_handler(req, res)
            return

        if check_intent(req, 'YANDEX.REJECT'):
            do_exit(req, res)
            return

        do_not_understand(req, res)
        return


def start_handler(req, res):
    user = req['userRecord']
    senders = user.get_senders

    # Получение числа отправителей
    M = len(senders)

    # Получение числа писем (общее)
    N = user.get_count_mail

    if N == 0:
        # Писем нет
        do_no_mails(req, res)
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
        do_error(req, res, str(N) + str(M))
        return


def prep_read_message(req, res, cont=False):
    # Подготовка содержания перед отправкой пользователю
    user = storage.get(req['session']['user_id'])
    mail = user.get_mail_from(user.num_sender, user.num_letter)
    content = 'Тема письма: ' + mail['subject'] + ' Текст письма: ' + mail['text']
    name = mail['from']

    if len(content.split()) > 30:
        if cont:
            content = ' '.join(content.split()[20:50])
            do_cont_mail(req, res, name, content)
        else:
            content = ' '.join(content.split()[:20])
            do_large_mail(req, res, name, content)
    else:
        do_small_mail(req, res, name, content)


def other_mails(req, res):
    # Проверка есть ли еще непрочитанные письма у пользователя
    # user = storage.get(req['session']['user_id'])
    # user.del_mail(user.num_sender, user.num_letter)
    # if not user.get_count_mail:
    #     do_no_more_mails(req, res)
    #     return
    do_any_more_mails(req, res)
    return


def get_number(req):
    # Получение первого числа из ответа пользователя

    if 'request' not in req:
        return False

    if 'nlu' not in req['request']:
        return False

    if 'tokens' not in req['request']['nlu'] or 'entities' not in req['request']['nlu']:
        return False

    for i in req['request']['nlu']['entities']:
        if i['type'] == 'YANDEX.NUMBER':
            return i['value']
    return False


def numerals(num, word):
    # Окончания числительных

    if (num > 10 and num < 20) or (num % 10 > 4) or (num % 10 == 0):
        # -ем
        if word == 'мо':
            return 'ем'
        if word == 'ами':
            return 'ами'
    if num % 10 > 1 and num % 10 < 5:
        # -ьма
        if word == 'мо':
            return 'ьма'
        if word == 'ами':
            return 'ами'
    if num % 10 == 1:
        # -ьмо
        if word == 'мо':
            return 'ьмо'
        if word == 'ами':
            return 'ой'
    return '*'


def do_error(req, res, msg):
    text = 'Ошибка. ' + msg
    res['response']['text'] += text


def do_not_understand(req, res):
    text = 'Я Вас не понимаю, повторите.'
    res['response']['text'] += text
    if 'state' in req and 'session' in req['state'] and 'value' in req['state']['session']:
        temp_state = req['state']['session']['value']
        save_state(res, temp_state)


def do_exit(req, res):
    text = 'Пока '
    res['response']['text'] += text
    res['response']['end_session'] = True


def do_help(req, res):
    text = 'Я могу проверить вашу почту, для этого просто скажите: "Проверить почту".'
    res['response']['text'] += text
    if 'state' in req and 'session' in req['state'] and 'value' in req['state']['session']:
        temp_state = req['state']['session']['value']
        save_state(res, temp_state)


# 0
def do_auth(req, res):
    text = 'Пожалуйста, авторизуйтесь с помощью телефона.'
    res['response']['text'] += text
    save_state(res, States.AUTH)
    res['start_account_linking'] = {}


# 1
def do_no_mails(req, res):
    # У вас нет новых писем

    text = 'У вас нет новых писем. '
    res['response']['text'] += text
    save_state(res, States.NoMAILS)
    do_any_help(req, res)


# 2
def do_one_mail(req, res):
    # У вас 1 новое письмо от Имя с темой тема. Вам прочитать это письмо?
    user = storage.get(req['session']['user_id'])
    user.num_sender = 0
    user.num_letter = 0
    mail = user.get_mail_from(0, 0)
    name = mail['from']
    topic = mail['subject']

    text = 'У вас 1 новое письмо от {0} с темой {1}. Вам прочитать это письмо? '.format(name, topic)
    res['response']['text'] += text
    save_state(res, States.OneMAIL)


# 3
def do_one_sender(req, res):
    # От имя пришло n1 писем с темами: 1. тема1 2. тема2. Назовите номер письма, содержание которого хотите прослушать
    user = storage.get(req['session']['user_id'])
    if not user.num_sender:
        user.num_sender = 0
    name = user.senders[user.num_sender]
    topics = user.get_sender_topics(user.num_sender)
    text = 'От {0} пришло {1} пис{2} с тем{3}: '.format(name, len(topics), numerals(len(topics), 'мо'), numerals(len(topics), 'ами'))
    for i in range(len(topics)):
        text += '{0}. {1} '.format(i + 1, topics[i])
    text += 'Назовите номер письма, содержание которого хотите прослушать. '
    res['response']['text'] += text
    save_state(res, States.OneSENDER)


# 4
def do_many_senders(req, res):
    # У вас: 1. n1 писем от Имя1 2. n2 писем от Имя2. Темы какого отправителя вы хотите прослушать? Можно назвать порядковый номер отправителя
    user = storage.get(req['session']['user_id'])
    Ntopics = user.get_senders
    names = list(Ntopics.keys())

    text = "У вас: "
    for i, name in enumerate(names):
        text += '{0}. {1} пис{3} от {2}. '.format(i + 1, Ntopics[name], name, numerals(Ntopics[name], 'мо'))
    text += 'Темы какого отправителя вы хотите прослушать? Можно назвать порядковый номер отправителя. '
    res['response']['text'] += text
    save_state(res, States.ManySENDERS)


# 5
def do_small_mail(req, res, name, content):
    # Письмо от Имя: (содержание)

    text = 'Письмо от {0}: {1}'.format(name, content)
    res['response']['text'] += text
    save_state(res, States.SmallMAIL)
    other_mails(req, res)


# 6
def do_large_mail(req, res, name, content):
    # Письмо от Имя: (содержание первые 20 слов). Это были первые 20 слов, дальше продолжать?

    text = 'Письмо от {}: {}. Это были первые 20 слов, продолжаю читать?'.format(name, content)
    res['response']['text'] += text
    save_state(res, States.LargeMAIL)


# 9
def do_cont_mail(req, res, name, content):
    # Продолжение письма от имя: (продолжение)

    text = 'Продолжение письма от {0}: {1}'.format(name, content)
    res['response']['text'] += text
    save_state(res, States.ContMAIL)
    other_mails(req, res)


# 7
def do_no_more_mails(req, res):
    # У вас больше нет новых сообщений

    text = 'У вас больше нет новых сообщений. '
    res['response']['text'] += text
    save_state(res, States.NoMoreMAIL)
    do_any_help(req, res)


# 8
def do_any_more_mails(req, res):
    # У вас еще есть непрочитанные сообщения, вы хотите их прослушать?

    text = 'У вас еще есть непрочитанные сообщения, прочитать их? '
    res['response']['text'] += text
    save_state(res, States.AnyMoreMAIL)


# 10
def do_any_help(req, res):
    # Я могу вам еще чем-то помочь? Проверить вашу почту еще раз?

    text = 'Я могу вам еще чем-то помочь? Проверить вашу почту еще раз? '
    res['response']['text'] += text
    save_state(res, States.AnyHELP)


def save_state(res, state):
    res['session_state'] = {'value': state}


def do_repeat(req, res):
    user = storage.get(req['session']['user_id'])
    text = user.last_said
    if not text:
        text = 'Я еще ничего не сказал.'
    res['response']['text'] += text
    if 'state' in req and 'session' in req['state'] and 'value' in req['state']['session']:
        temp_state = req['state']['session']['value']
    save_state(res, temp_state)


def check_intent(req, tag):
    return 'request' in req and 'nlu' in req['request'] and 'intents' in req['request']['nlu'] and tag in req['request']['nlu']['intents']

