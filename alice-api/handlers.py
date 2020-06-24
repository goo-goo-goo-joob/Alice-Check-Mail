def handler(event, context):
    """
    Entry-point for Serverless Function.
    :param event: request payload.
    :param context: information about current execution context.
    :return: response to be serialized as JSON.
    """
    text = 'Hello! I\'ll repeat anything you say to me.'
    if 'request' in event and 'original_utterance' in event['request'] and len(
            event['request']['original_utterance']) > 0:
        text = event['request']['original_utterance']
    context['response']['text'] = text

    if 'access_token' not in event['session']['user']:
        context['start_account_linking'] = {}
