# email.py
# email 전송하는 python module

from threading import Thread
from flask import current_app, render_template
from flask_mail import Message
from . import mail


def send_aysnc_email(app, msg):
    with app.app_context():
        mail.send(msg)


# def send_email():
#     app = current_app._get_current_object()
#     msg = Message('Test send email Message', sender='Team ACD admin', recipients=['sys3948@naver.com'])

#     msg.body = 'Test Flask send email'
#     msg.html = '<h1>Test Flask send email</h1>'

#     thr = Thread(target=send_aysnc_email, args=[app, msg])
#     thr.start()

#     return thr

def send_email(to, title, templates, **kwargs):
    app = current_app._get_current_object()
    msg = Message(title, sender='Team ACD admin', recipients=[to])

    msg.body = render_template(templates+'.txt', **kwargs)
    msg.html = render_template(templates+'.html', **kwargs)

    thr = Thread(target=send_aysnc_email, args=[app, msg])
    thr.start()

    return thr