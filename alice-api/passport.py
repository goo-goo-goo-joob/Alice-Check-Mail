import json
import requests


def _get_user_info(token):
    r = requests.get('https://login.yandex.ru/info?format=json',
                     headers={'Authorization': 'Bearer {}'.format(token)}
                     )
    if r.ok:
        return json.loads(r.text)


def get_user_email(token):
    info = _get_user_info(token)
    return info['default_email']
