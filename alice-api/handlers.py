from .mail import get_all_mail

def handler(event, context):
    """
    Entry-point for Serverless Function.
    :param event: request payload.
    :param context: information about current execution context.
    :return: response to be serialized as JSON.
    """
    # Приветствуем нового пользователя
    if event['session']['new']:
        text = 'Я могу проверить вашу почту, просто скажите мне об этом.'

    if 'request' in event and 'original_utterance' in event['request'] and len(
            event['request']['original_utterance']) > 0:
        text = event['request']['original_utterance']
    context['response']['text'] = text

    if 'access_token' not in event['session']['user']:
        context['start_account_linking'] = {}
