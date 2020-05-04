import os

import requests
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader


class BaseParser:
    parser = "html.parser"
    def __init__(self, url, output='test.html'):
        self.header = ''
        self.subheader = ''
        self.content = []
        self.always_visible_content = []
        self.rest_of_content = []
        self.success = False
        r = requests.get(url)
        self.code = r.status_code
        if r.status_code != 200:
            print(f'Status code: {r.status_code}')
            return
        self.soup = BeautifulSoup(r.text, self.parser)
        self.parse_header()
        self.parse_content()
        if len(self.content) >= 3:
            self.split_content()
        if all((self.header, self.content)):
            self.render_template(output)

    def split_content(self):
        divider = int(len(self.content)/3)
        self.always_visible_content = self.content[:divider]
        self.always_visible_content[-1] = self.always_visible_content[-1].replace(
            '<p>', '<p {% if not paywall.show %} class="paytext" {% endif %}>', 1)
        self.rest_of_content = self.content[divider:]

    def trim_text(self, text):
        text = self.split_and_filter_text(text)
        return '\n'.join(text)

    def split_and_filter_text(self, text):
        return [i for i in text.split('\n') if i]

    def parse_header(self):
        pass

    def parse_content(self):
        pass

    def render_template(self, output_path='test.html'):
        try:
            path_to_template = os.path.join('templates', 'generatednews')
            file_loader = FileSystemLoader(path_to_template)
            env = Environment(loader=file_loader)
            template = env.get_template('basetemplate.html')
            avc = self.always_visible_content
            roc = self.rest_of_content
            output = template.render(header=self.header, subheader=self.subheader,
                                     always_visible_content=avc, rest_of_content=roc)
            with open(output_path, 'w', encoding='utf-8') as f:
                print(output, file=f)
            self.success = True
        except Exception as e:
            print(e)

class GuardianParser(BaseParser):

    def __init__(self, url, output='test.html'):
        super().__init__(url, output=output)


    def parse_header(self):
        for header in self.soup.find_all('header', class_='content__head'):
            for h1 in header.find_all('h1', class_='content__headline',limit=1):
                self.header = h1.text.strip()
            for header_div in header.find_all('div', class_='content__standfirst'):
                self.subheader = header_div.text.strip()

    def parse_content(self):
        contents = []
        for div in self.soup.find_all('div', class_='content__article-body'):
            for child in div.children:
                if child.name == 'p':
                    contents.append(str(child))
                if child.name == 'figure':
                    try:
                        for div in child.find_all('div'):
                            # div.attrs.get if below doesnt work
                            if 'block-share' in div.get('class', []):
                                div.extract()
                            div['style'] = None
                        [i.extract() for i in child.find_all('span')]
                        contents.append(str(child))
                    except:
                        pass
        self.content = contents


class PoliticoParser(BaseParser):


    def parse_header(self):
        for h2 in self.soup.find_all('h2'):
            self.header = h2.text.strip()
        p = self.soup.find('p', class_='dek')
        self.subheader = p.text.strip()

    def parse_content(self):
        for figure in self.soup.find_all('figure', class_='art'):
            self.content.append(str(figure))
            break
        for div in self.soup.find_all('div', class_='story-text'):
            for child in div.children:
                if child.name in ['p', 'figure']:
                    self.content.append(str(child))


class TheVergeParser(BaseParser):

    def parse_header(self):
        for h1 in self.soup.find_all('h1'):
            self.header = h1.text.strip()
        p = self.soup.find('p', class_='p-dek')
        self.subheader = p.text.strip()

    def parse_content(self):
        figure = self.soup.find('figure', class_='e-image')
        self.content.append(str(figure)) if figure else None
        div = self.soup.find('div', class_='c-entry-content')
        for child in div.children:
            if child.name in ['p', 'figure']:
                self.content.append(str(child))

class EngadgetParser(BaseParser):

    def parse_header(self):
        h1 = self.soup.find('h1', class_='t-h4@m-')
        self.header = h1.text.strip()
        div = self.soup.find('div', class_='t-d7@m-')
        self.subheader = div.text.strip()

    def parse_content(self):
        div = self.soup.find('div', id='page_body')
        for child in div.descendants:
            if child.name in ['p', 'img', 'image']:
                if child.get('alt', '').lower() not in ['share', 'like', 'comment']:
                    self.content.append(str(child))

class UsaTodayParser(BaseParser):

    def parse_header(self):
        h1 = self.soup.find('h1', class_='title')
        self.header = h1.text.strip()

    def parse_content(self):
        div = self.soup.find('div', class_='article-wrapper')
        for child in div.children:
            if child.name in ['p', 'h2']:
                self.content.append(str(child))
            if child.name == 'div' and 'asset-image' in child.get('class', ''):
                self.content.append(str(child))

if __name__ == '__main__':
    urls= [
        'https://www.politico.com/news/2020/05/03/can-joe-bidens-team-make-him-go-viral-228706'
        ]
    for url in urls:
        gp = PoliticoParser(url)
        print(f'Success: {gp.success}')
