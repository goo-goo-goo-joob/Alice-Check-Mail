import base64
import email
import imaplib
import re

from bs4 import BeautifulSoup

pattern = re.compile(r'\s+')


class ReadException(Exception):
    pass


class ImapException(Exception):
    pass


def decode_mail(msg):
    if isinstance(msg.get_payload(), list):
        return '\n'.join([decode_mail(m) for m in msg.get_payload()])
    text = msg.get_payload(decode=True)
    if isinstance(text, bytes):
        try:
            text = text.decode('utf-8')
        except UnicodeDecodeError:
            text = msg.get_payload()
    if msg.get_content_type() == 'text/html':
        bs = BeautifulSoup(text, 'html5lib')
        body = bs.find('body')
        if body is None:
            text = bs.text
        else:
            text = body.text
    else:
        text = ''
    text = pattern.sub(' ', text.replace('\n', ''))
    return text


class YandexIMAP(imaplib.IMAP4_SSL):
    """
    Этот класс предназначен только для хождения в почту.
    """

    def __init__(self):
        super().__init__('imap.yandex.ru', 993)

    def _command_xoauth2(self, token):
        if self.state not in imaplib.Commands['AUTHENTICATE']:
            self.literal = None
            raise self.error("command AUTHENTICATE illegal in state , "
                             "only allowed in states %s" % self.state)

        for typ in ('OK', 'NO', 'BAD'):
            if typ in self.untagged_responses:
                del self.untagged_responses[typ]

        if 'READ-ONLY' in self.untagged_responses \
                and not self.is_readonly:
            raise self.readonly('mailbox status changed to READ-ONLY')

        tag = self._new_tag()
        data = tag + b' AUTHENTICATE XOAUTH2 ' + token

        literal = self.literal
        if literal is not None:
            self.literal = None
            if type(literal) is type(self._command):
                literator = literal
            else:
                literator = None
                data = data + bytes(' {%s}' % len(literal), self._encoding)

        try:
            self.send(data + imaplib.CRLF)
        except OSError as val:
            raise self.abort('socket error: %s' % val)

        if literal is None:
            return tag

        while 1:
            # Wait for continuation response

            while self._get_response():
                if self.tagged_commands[tag]:  # BAD/NO?
                    return tag

            # Send literal

            if literator:
                literal = literator(self.continuation_response)

            try:
                self.send(literal)
                self.send(imaplib.CRLF)
            except OSError as val:
                raise self.abort('socket error: %s' % val)

            if not literator:
                break

        return tag

    def xoauth2(self, email_addr, token):
        phrase = 'user={}\001auth=Bearer {}\001\001'.format(email_addr, token)
        phrase = base64.b64encode(phrase.encode('utf-8'))
        typ, dat = self._command_complete('AUTHENTICATE', self._command_xoauth2(phrase))
        if typ != 'OK':
            raise ImapException(dat[-1].decode('utf-8', 'replace'))
        self.state = 'AUTH'
        return typ, dat

    def select_msg(self, num):
        typ, data = self.fetch(num, '(RFC822)')
        if typ == 'OK':
            return email.message_from_string(data[0][1].decode('utf-8'))
        else:
            self.error('can\'t get message number {}: {}'.format(num, typ))

    def get_all_mail(self):
        """
        Эта функция должна собрать и вернуть всю почту.
        """
        # Флаг readonly нужен для непроставления статуса "прочитанно"
        self.select('INBOX', readonly=True)
        # Выбираем только непрочитанные
        ok, messages = self.search(None, '(UNSEEN)')
        if ok != 'OK':
            raise ReadException('Нельзя прочитать входящие сообщения')
        # Возвращает байтовую стоку с ID сообщений, фильтр требуется для корректной обработке пустого результата
        all_mails = []
        for num in filter(None, messages[0].split(b' ')):
            unit_mail = {}
            # Получаем сообщения класса email.message.Message.
            msg = self.select_msg(num)
            unit_mail['raw'] = msg
            # Декодируем тему
            unit_mail['subject'] = email.header.decode_header(msg['Subject'])[0]
            if isinstance(unit_mail['subject'][0], bytes):
                unit_mail['subject'] = unit_mail['subject'][0].decode(unit_mail['subject'][1])
            else:
                unit_mail['subject'] = unit_mail['subject'][0]
            # Декодируем отправителя (может потеряться адрес отправителя)
            unit_mail['from'] = email.header.decode_header(msg['From'])[0]
            if isinstance(unit_mail['from'][0], bytes):
                unit_mail['from'] = unit_mail['from'][0].decode(unit_mail['from'][1])
            else:
                unit_mail['from'] = unit_mail['from'][0]
            try:
                # Сообщение может состоять из серии сообщений, поэтому для корректной отработки понадобится
                # рекурсивно пройтись по всем пэйлоадам и декодировать их.
                unit_mail['text'] = decode_mail(msg)
            except Exception as e:
                unit_mail['text'] = 'К сожалению, такое я еще читать не научился.'
            all_mails.append(unit_mail)
        return all_mails
