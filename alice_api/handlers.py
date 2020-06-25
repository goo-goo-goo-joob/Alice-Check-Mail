from enum import Enum, auto

class States(Enum):
    START = auto()
    CHECK = auto()
    AUTH = auto() # 0
    NoMAILS = auto() # 1
    OneMAIL = auto() # 2
    OneSENDER = auto() # 3
    ManySENDERS = auto() # 4
    SmallMAIL = auto() # 5
    LargeMAIL = auto() # 6
    ContMAIL = auto() # 9
    NoMoreMAIL = auto() # 7
    AnyMoreMAIL = auto() # 8
    AnyHELP = auto() # 10

def do_error(req, res):
    text = 'Error!!! '
    res['response']['text'] += text

def do_auth(req, res):

    #TODO: Здесь должна быть авторизация

    text = 'Я могу проверить вашу почту, просто скажите мне об этом. '
    res['response']['text'] += text
    res['user_state_update'] = States.AUTH

def do_no_mails(req, res):

    # У вас нет новых писем

    text = 'У вас нет новых писем. '
    res['response']['text'] += text
    res['user_state_update'] = States.NoMAILS

def do_one_mail(req, res, name, topic):

    # У вас 1 новое письмо от Имя с темой тема. Вам прочитать это письмо?

    text = 'У вас 1 новое письмо от {0} с темой {1}. Вам прочитать это письмо? '.format(name, topic)
    res['response']['text'] += text
    res['user_state_update'] = States.OneMAIL

def do_one_sender(req, res, name, topics):

    # От имя пришло n1 писем с темами: 1. тема1 2. тема2. Назовите номер письма, содержание которого хотите прослушать
    # TODO: числительные

    text = 'От {0} пришло {1} писем с темами: '.format(name, len(topics))
    for i in range(len(topics)):
        text += '{0}. {1} '.format(i+1, topics[i])
    text += 'Назовите номер письма, содержание которого хотите прослушать. '
    res['response']['text'] += text
    res['user_state_update'] = States.OneSENDER

def do_many_senders(req, res, names, Ntopics):

    #У вас: 1. n1 писем от Имя1 2. n2 писем от Имя2. Темы какого отправителя вы хотите прослушать? Можно назвать порядковый номер отправителя
    # TODO: числительные

    text = "У вас: "
    for i, name in enumerate(names):
        text += '{0}. {1} писем от {2}.'.format(i+1, Ntopics[name], name)
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