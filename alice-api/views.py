from flask import request
import json
from . import app
from .handlers import handler


@app.route('/', methods=['POST'])
def main():
    response = {
        "version": request.json['version'],
        "session": request.json['session'],
        "response": {
            "end_session": False
        }
    }

    handler(request.json, response)

    return json.dumps(
        response,
        ensure_ascii=False,
        indent=2
    )
