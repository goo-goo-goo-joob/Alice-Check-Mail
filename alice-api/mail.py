import base64
import email
import imaplib
import os

from .passport import get_user_email


class YandexIMAP(imaplib.IMAP4_SSL):
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
            raise self.error(dat[-1].decode('utf-8', 'replace'))
        self.state = 'AUTH'
        return typ, dat

    def select_msg(self, num):
        typ, data = self.fetch(num, '(RFC822)')
        if typ == 'OK':
            return email.message_from_string(data[0][1].decode('utf-8'))
        else:
            self.error('can\'t get message number {}: {}'.format(num, typ))


def get_all_mail():
    '''
    Эта функция должна собрать и вернуть всю почту.
    '''
    token = os.getenv('TOKEN')
    email_addr = get_user_email(token)
    imap = YandexIMAP()
    imap.xoauth2(email_addr, token)
    # Надо последовательно выбрать все ящики
    ok, boxes = imap.list()
    if ok != ok:
        raise imap.error('can\'t get list: {}'.format(ok))
    for box in boxes:
        box = box.decode().split(' "|" ')[1]
        print('USE ', box)
        # Теоретически, может вернуть количество непрочитанных сообщений
        # Флаг readonly нужен для непроставления статуса "прочитанно"
        imap.select(box, readonly=True)
        # Выбираем только непрочитанные
        ok, messages = imap.search(None, '(UNSEEN)')
        if ok != 'OK':
            print('Can\'t get box {}'.format(box))
        # Возвращает байтовую стоку с ID сообщений, фильтр требуется для корректной обработке пустого результата
        for num in filter(None, messages[0].split(b' ')):
            # Получаем сообщения класса email.message.Message.
            msg = imap.select_msg(num)
            # Декодируем тему
            try:
                print(email.header.decode_header(msg['Subject'])[0][0].decode('utf-8'))
            except:
                print(email.header.decode_header(msg['Subject'])[0][0])
            # Декодируем отправителя (может потеряться адрес отправителя)
            try:
                print(email.header.decode_header(msg['From'])[0][0].decode('utf-8'))
            except:
                print(email.header.decode_header(msg['From'])[0][0])
            try:
                # Сообщение может состоять из серии сообщений, поэтому для корректной отработки понадобится
                # рекурсивно пройтись по всем пэйлоадам и декодировать их.
                # Может встречаться html, надо подумать над BeautifulSoap
                print(msg.get_payload(decode=True).decode('utf-8'))
            except:
                print('Too deep')
            print('----------')
        print('-' * 60)
    imap.close()
    return
