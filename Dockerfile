FROM mcr.microsoft.com/playwright/python:v1.30.0-focal-amd64

ENV PIP_ROOT_USER_ACTION=ignore

WORKDIR /opt/app
ADD . .

RUN pip install --upgrade pip && pip install -r requirements.txt

ENTRYPOINT ["/opt/app/entrypoint.sh"]
