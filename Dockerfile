FROM snakepacker/python:all as builder
RUN python3.7 -m venv /usr/share/python3/app
RUN /usr/share/python3/app/bin/pip install -U pip

COPY requirements.txt /mnt/
RUN /usr/share/python3/app/bin/pip install -Ur /mnt/requirements.txt

COPY dist/ /mnt/dist/
RUN /usr/share/python3/app/bin/pip install /mnt/dist/* && /usr/share/python3/app/bin/pip check

FROM snakepacker/python:3.7 as api

COPY --from=builder /usr/share/python3/app /usr/share/python3/app

ENV FLASK_APP=alice-api/__init__.py
CMD ["flask run"]