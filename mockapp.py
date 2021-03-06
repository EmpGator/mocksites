import os
import sqlite3
import requests
from flask import Flask, session, render_template, redirect, url_for, request, make_response, flash, jsonify
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired

from article_parsers import GuardianParser, PoliticoParser, TheVergeParser, EngadgetParser, UsaTodayParser

app = Flask(__name__)
app.secret_key = b'dsaadsads'
finnplus_domain = 'https://erolkazanjyu.pythonanywhere.com'
mockapp_domain = 'http://tridample.eu.pythonanywhere.com'
tablename = './mock.db'


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
    print(payload)
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


def pay_article(url, domain, article_info={}):
    request_url = finnplus_domain + '/api/payarticle'
    payload = {'url': url, 'domain': domain, **article_info}
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
@app.route('/<site>/logout')
def logout(site=None):
    """logout route"""
    session['user'] = None
    session['accessToken'] = None
    url = url_for('index')
    if request.referrer is not None:
        url = request.referrer
    return render_template('logout_finnplus.html', url_to=url)


@app.route('/')
def index():
    return make_response('404', 404)
    _, data = get_info(url=request.referrer, domain=request.referrer)
    return render_template('index.html', data=data)


@app.route('/finnplus', methods=['POST'])
def finnplus():
    """ This informs finnplus that article has been paid """
    print('Posting to paidarticle')
    data = request.json
    domain = data['url'][:-10]
    data = pay_article(data['url'], domain)
    if not data.get('payment_successful'):
        return make_response('Payment failed', 403)
    return jsonify(data)



@app.context_processor
def utility_processor():
    return dict(finnplus_domain=finnplus_domain)


@app.route('/setcookie/<jwt>')
def setcookie(jwt=None):
    session['accessToken'] = jwt
    return make_response('ok', 200)

@app.route('/<site>/setcookie/<jwt>')
def setcookiesite(site=None, jwt=None):
    session['accessToken'] = jwt
    return make_response('ok', 200)


@app.route('/<site>/')
def front(site='mock'):
    if site == 'favicon.ico':
        return redirect(url_for('static', filename='favicon.ico'))
    if site not in ['news', 'theothernews', 'waldonews']:
        return make_response('404', 404)
    _, data = get_info(request.url)
    try:
        data['message'].replace('tokens', 'articles')
    except:
        pass
    return render_template(f'{site}/index.html', data=data)


@app.route('/<site>/article/<id>')
def news(site='mock', id=0):
    if site not in ['news', 'theothernews', 'waldonews', 'generatednews']:
        return make_response('404', 404)
    print('Checking if content is can be paid')
    domain = f'{mockapp_domain}/{site}'
    art_data = {
        'url': f'{domain}/article/{id}',
        'domain': domain,
        'article_name': 'Mallinimi',
        'article_date': '2019-08-22',
        'article_desc': 'Pitkäkuvaus',
        'article_category': 'sports'
    }
    show, data = get_info(request.url, domain=domain, article_data=art_data)
    pay = False
    #if data.get('method') == 'Monthly Subscription':
        #pay = False
    if not data.get('access') and data.get('can_pay'):
        pay = True

    try:
        data['message'].replace('tokens', 'articles')
    except:
        print(data.get('message'))

    return render_template(f'{site}/article_{id}.html', paywall=show, data=data, pay=pay)


@app.route('/<site>/rss')
def generate_rss(site='mock'):
    if site not in ['news', 'theothernews', 'waldonews']:
        return make_response('404', 404)
    from jinja2 import TemplateNotFound
    try:
        template = render_template(f'{site}/rss.xml')
    except TemplateNotFound:
        feed = generate_feed(site, request.url)
        template = render_template('base.xml', feed=feed)
    resp = make_response(template)
    resp.headers['Content-Type'] = 'application/xml'
    return resp


@app.route('/check_urls', methods=['POST'])
def check_urls():
    data = request.get_json()
    if data:
        urls = data.get('urls')
    else:
        urls = request.data.get('urls', None)
    if not urls:
        return jsonify({})
    res_data = {'existing': {}, 'not_existing': []}

    db_urls = get_urls()
    db_urls = {i[1]: i[2] for i in db_urls}
    print(len(urls))
    for url in urls:
        mock_url = db_urls.get(url, None)
        if mock_url:
            # url in db means that generated article exists
            # add url to res_data['existing'][url] = mock_url
            res_data['existing'][url] = mock_url
        else:
            res_data['not_existing'].append(url)
    return jsonify(res_data)

@app.route('/generate_article', methods=['POST'])
def generate_article_from_data():
    data = request.get_json()
    resp = {}
    conn = sqlite3.connect(tablename)
    c = conn.cursor()
    db_urls = get_urls()
    max_id = max([i[0] for i in db_urls] or [0])
    for item in data:
        try:
            url = item.get('url')
            header = item.get('header')
            subheader = item.get('subheader')
            avc = item.get('avc')
            roc = item.get('roc')
            output = render_template('generatednews/basetemplate.html', header=header, subheader=subheader,
                                     always_visible_content=avc, rest_of_content=roc)
            output_path = f'./templates/generatednews/article_{max_id}.html'
            output_url = f'{mockapp_domain}/generatednews/article/{max_id}'

            with open(output_path, 'w', encoding='utf-8') as f:
                print(output, file=f)
            resp[url] = output_url
            max_id += 1
            c.execute('INSERT INTO urls (original_url, url) VALUES (?, ?)', (url, output_url))

        except Exception as e:
            print(e)

    conn.commit()
    conn.close()
    return jsonify(resp)

def get_urls():
    conn = sqlite3.connect(tablename)
    c = conn.cursor()
    c.execute('SELECT * FROM urls')
    urls = c.fetchall() or []
    conn.close()
    return urls

def generate_table():
    try:
        conn = sqlite3.connect(tablename)
        c = conn.cursor()
        c.execute('''CREATE TABLE urls
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 original_url TEXT,
                 url TEXT);''')
        conn.commit()
    except Exception as e:
        print(e)

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

    try:
        import os
        filepath = os.path.join('templates', site, 'rss.xml')
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(render_template('base.xml', feed=feed).replace(' ', ' '))
    except Exception as e:
        print('error: ', e)


generate_table()
if __name__ == '__main__':

    app.run(port=8000)
