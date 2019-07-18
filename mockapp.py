from flask import Flask, session, render_template, redirect, url_for, request, make_response, flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired
import requests

app = Flask(__name__)
app.secret_key = b'dsaadsads'
finnplus_domain = 'http://127.0.0.1:5000'

class LoginForm(FlaskForm):
    name = StringField('name', validators=[DataRequired()])
    password = PasswordField('password', validators=[DataRequired()])


class Paywall:
    def __init__(self):
        self.show = False
        self.pay = False
        self.block = True

    def set_show(self):
        self.show = True
        self.pay = False
        self.block = False
        return self

    def set_pay(self):
        self.show = False
        self.pay = True
        self.block = False
        return self

    def set_block(self):
        self.show = False
        self.pay = False
        self.block = True
        return self

    def __str__(self):
        if self.show:
            return  'Paywall Show'
        elif self.pay:
            return 'Paywall Show'
        return 'Paywall block'

def show_content(url):
    auth = session.get('user', None)
    paywall = Paywall()
    payload = {'url': url}
    if not auth:
        print('not auth')
        jwt = session.get('accessToken', '')
        print(jwt)
        headers = {'Authorization': f'Bearer {jwt}'}
        r = requests.post(finnplus_domain + '/api/userdata', data=payload, headers=headers)
    else:
        print('auth', auth)
        r = requests.post(finnplus_domain + '/api/userdata', data=payload, auth=auth)
    if r.status_code == 200:
        print('r 200')
        data = r.json()
        if data['access']:
            return paywall.set_show()
        return paywall.set_pay()
    else:
        print(r.status_code)
        print(r.text)
    return paywall


def get_info():
    print('get info')
    auth = session.get('user', None)
    if not auth:
        print('not auth')
        jwt = session.get('accessToken')
        if not jwt:
            print('not jwt')
            return None
        headers = {'Authorization': f'Bearer {jwt}'}
        r = requests.post(finnplus_domain + '/api/userinfo', headers=headers)
    else:
        r = requests.post(finnplus_domain + '/api/userinfo', auth=auth)
    if r.status_code == 200:
        print('r 200')
        data = r.json()
        print(data)
        session['name'] = data.get('name')
        session['payment_type'] = data.get('payment_type')
        session['value'] = data.get('value')
        return data

def test(url='', pay=False):
    print('unified userinfo and pay test')
    auth = session.get('user', None)
    paywall = Paywall()
    payload = {'url':url, 'domain':url, 'pay':pay}
    print(f'Payload: {payload}')
    if not auth:
        print('not auth')
        jwt = session.get('accessToken')
        if not jwt:
            print('not jwt')
            return None, None
        headers = {'Authorization': f'Bearer {jwt}'}
        r = requests.post(finnplus_domain + '/api/test', headers=headers, json=payload)
    else:
        r = requests.post(finnplus_domain + '/api/test', auth=auth, json=payload)
    if r.status_code == 200:
        print('r 200')
        data = r.json()
        print(data)
        session['name'] = data.get('name')
        session['payment_type'] = data.get('payment_type')
        session['value'] = data.get('value')
        data = r.json()
        if data['access']:
            return paywall.set_show(), data
        return paywall.set_pay(), data
    else:
        print(r.status_code)
    return paywall, {}




@app.route('/loginfinnplus', methods=['POST'])
def loginfinnplus():
    """ handles login with finn plus account"""
    user = request.form.get('name')
    password = request.form.get('password')
    session['user'] = (user, password)
    return redirect(request.referrer)


@app.route('/logout')
def logout():
    """logout route"""
    session['user'] = None
    session['accessToken'] = None
    url = url_for('index')
    if request.referrer is not None:
        url = request.referrer
    return render_template('logout_finnplus.html', url_to=url)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/finnplus', methods=['POST'])
def finnplus():
    """ This informs finnplus that article has been paid """
    print('Posting to paidarticle')
    data = request.get_json()
    auth = session.get('user', None)

    if auth:
        r = requests.post(finnplus_domain + '/api/articlepaid',
                          auth=auth, data=data)
    else:
        jwt = session.get('accessToken', '')
        headers = {'Authorization': f'Bearer {jwt}'}
        data['pay'] = True
        r = requests.post(finnplus_domain + '/api/articlepaid',
                          headers=headers, json=data)
    #data = r.json() data.get('message') != 'ok'
    if r.text.strip() == "Not enough tokens":
        flash('Not enough tokens')
    return make_response('ok', 200)


@app.context_processor
def utility_processor():
    def get_user_data():
        return get_info()
    return dict(get_user_data=get_user_data, finnplus_domain=finnplus_domain)


@app.route('/setcookie/<jwt>')
def setcookie(jwt=None):
    url_to = request.args.get('url_to')
    print(jwt)
    session['accessToken'] = jwt
    if url_to == None:
        return redirect(url_for('index'))
    return redirect(url_to)


@app.route('/rss')
def rss():
    return render_template('news_app.xml')

@app.route('/<site>/')
def front(site='mock'):
    if site == 'favicon.ico':
        return redirect(url_for('static', filename='favicon.ico'))
    _, data = test(request.url)
    return render_template(f'{site}/index.html')


@app.route('/<site>/article/<id>')
def news(site='mock', id=0):
    print('show content')
    show = show_content(str(request.url))
    #show, data = test(request.url)
    #print(show, data)
    return render_template(f'{site}/article_{id}.html', paywall=show)

if __name__ == '__main__':
    app.run(port=8000)
