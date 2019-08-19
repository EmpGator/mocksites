from flask import Flask, session, render_template, redirect, url_for, request, make_response, flash, jsonify
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired
import requests

app = Flask(__name__)
app.secret_key = b'dsaadsads'
finnplus_domain = 'http://127.0.0.1:5000'
mockapp_domain = 'http://127.0.0.1:5000'


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
            return 'Paywall Show'
        elif self.pay:
            return 'Paywall Show'
        return 'Paywall block'


def get_response(payload, request_url):

    auth = session.get('user', None)
    jwt = session.get('accessToken')
    if auth:
        print('Getting response from finnplus with')
        print(f'User: {auth}')
        r = requests.post(request_url, auth=auth, json=payload)
    elif jwt:
        print('Getting response from finnplus with')
        print(f'jwt {jwt}')
        headers = {'Authorization': f'Bearer {jwt}'}
        r = requests.post(request_url, headers=headers, json=payload)
    else:
        print('no auth or jwt aboprting request')
        r = None
    return r


def get_info(url='', domain='', article_data={}):
    print('Asking userinfo from finnpluss')
    paywall = Paywall()
    payload = {'url': url, 'domain': domain, **article_data}
    request_url = finnplus_domain + '/api/userinfo'
    r = get_response(payload, request_url)
    if not r:
        print('No response, blocking content')
        return paywall, {}
    elif r.status_code == 200:
        print('Response was good, getting access data')
        data = r.json()
        print('Access: ', data['access'])
        if data['access']:
            print('Access allowed')
            return paywall.set_show(), data
        elif data.get('can_pay'):
            print('Access not allowed, but user can pay, request payment')
            return paywall.set_show(), data
        else:
            print('User cant pay')
            return paywall.set_pay(), data
    else:
        print(f'Request to {request_url} failed')
        print(r.status_code)
        print(r.text)
    return paywall, {}


def pay_article(url, domain):
    request_url = finnplus_domain + '/api/payarticle'
    payload = {'url': url, 'domain': domain}
    resp = get_response(payload, request_url)
    if resp and resp.status_code == 200:
        return resp.json()
    print('Request to payarticle failed')
    print(resp.text)
    return {}


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
    _, data = get_info(url=request.referrer, domain=request.referrer)
    return render_template('index.html', data=data)


@app.route('/finnplus', methods=['POST'])
def finnplus():
    """ This informs finnplus that article has been paid """
    print('Posting to paidarticle')
    data = request.json
    domain = data['url'][:-10]
    data = pay_article(data['url'], domain)
    print(data)
    if not data.get('payment_successful'):
        return make_response(403)
    return jsonify(data)



@app.context_processor
def utility_processor():
    return dict(finnplus_domain=finnplus_domain)


@app.route('/setcookie/<jwt>')
def setcookie(jwt=None):
    session['accessToken'] = jwt
    return make_response('ok', 200)


@app.route('/<site>/')
def front(site='mock'):

    if site == 'favicon.ico':
        return redirect(url_for('static', filename='favicon.ico'))
    _, data = get_info(request.url)
    print(data)
    return render_template(f'{site}/index.html', data=data)


@app.route('/<site>/article/<id>')
def news(site='mock', id=0):
    print('Checking if content is can be paid')
    domain = f'{mockapp_domain}/{site}'
    art_data = {
        'article_name': None,
        'article_date': None,
        'article_desc': None,
        'article_category': None
    }
    show, data = get_info(request.url, domain=domain, article_data=art_data)
    pay = False
    if data.get('method') == 'Monthly Subscription':
        pay = False
    elif not data.get('access') and data.get('can_pay'):
        pay = True

    return render_template(f'{site}/article_{id}.html', paywall=show, data=data, pay=pay)


@app.route('/<site>/rss')
def generate_rss(site='mock'):
    from jinja2 import TemplateNotFound
    try:
        template = render_template(f'{site}/rss.xml')
    except TemplateNotFound:
        feed = generate_feed(site, request.url)
        template = render_template('base.xml', feed=feed)
    resp = make_response(template)
    resp.headers['Content-Type'] = 'application/xml'
    return resp


def generate_feed(site, request_url):
    from bs4 import BeautifulSoup
    from random import choice, randint
    from datetime import timedelta, date
    base_url = request_url.replace('rss', 'article')
    domain = request_url.replace('/rss', '')
    url_list = [base_url + f'/{j}' for j in range(10)]
    feed = dict(name=site, domain=domain, desc=None, entries=[], rss=request_url)
    categories = ['politics', 'sports', 'economy', 'technology', 'health', 'entertainment']
    for i, url in enumerate(url_list):
        r = requests.get(url, auth=('admin', 'test'))
        soup = BeautifulSoup(r.content)
        imgs = soup.find_all('img')
        if len(imgs) >= 3:
            img = imgs[1].get('src')
            if not img:
                try:
                    img = imgs[1].get('srcset').split(',')[-1:][0].split(' ')[1]
                except IndexError:
                    print('index error')
                    img = ''
        else:
            img = ''
        try:
            desc = ' '.join(soup.find_all(attrs={'class': 'paytext'})[0].get_text().strip().split(' '))
        except IndexError:
            desc = ''
        try:
            title = ' '.join(soup.find_all('h1')[0].get_text().strip().split(' '))
        except IndexError:
            title = ''
        category = choice(categories)
        day = date(2019, 5, 1) + timedelta(days=randint(0, 83))
        feed['entries'].append({'title': title, 'mediaurl': img, 'desc': desc, 'category': category,
                                'url': url, 'guid': i, 'date': day})

    with open('test.xml', 'w') as f:
        f.write(render_template('base.xml', feed=feed))


if __name__ == '__main__':
    app.run(port=8000)
