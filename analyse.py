import requests
import hashlib
from pprint import pprint
import json
from collections import defaultdict

from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

BASE_URL = 'http://www.cdep.ro/pls/legis/'

TYPES = {
    'LEGE': 1,
    'OUG': 13,
}

REVERSE_TYPES = {v: k for k, v in TYPES.items()}

URLS = {
    1: '{}legis_pck.lista_anuala?emi=2&tip={}&rep=0&an='.format(BASE_URL, TYPES['LEGE']),
    13: "{}legis_pck.lista_anuala?emi=3&tip={}&rep=0&an=".format(BASE_URL, TYPES['OUG']),
}


def hash_url(text):
    result = hashlib.md5(text.encode())
    return result.hexdigest()


def get_page(url):
    filename = hash_url(url)
    path = "./htmls/{}.html".format(filename)
    try:
        with open(path, "r") as html_file:
            data = html_file.read()
    except FileNotFoundError:
        print("Get url {}".format(url))
        r = requests.get(url)
        data = '<!-- {} -->\n\n{}'.format(url, r.text)

        with open(path, "w") as html_file:
            html_file.write(data)

    return data


def extract_link(td):
    href = td.find('a', href=True, )
    id_act = url = None
    if href:
        href = href.get('href')
        url = urlparse(href)
        if url.path == 'legis_pck.htp_act':
            params = parse_qs(url.query)
            id_act = params.get('ida', [])[0]

    return id_act


def extract_info(data):
    html = BeautifulSoup(data, 'lxml')
    expected = ('Abrogă:', 'Modifică:', 'Promulgată:', 'Modificată:', "Abrogată:")
    info = defaultdict(list)

    text = html.find(text="Functie activa:")
    if not text:
        text = html.find(text="Functie pasivă:")

    if not text:
        return []

    table = text.find_parent("table")

    rows = table.find_all('tr', recursive=False)
    current_col = ''
    for row in rows:
        columns = row.find_all('td', recursive=False)

        if len(columns) < 3:
            continue

        column1 = columns[0].get_text().strip()
        if column1 in expected:
            current_col = column1
            u = extract_link(columns[1])
            info[current_col].append(u)
        elif column1 == '' or column1 == '&nbsp;' and current_col in expected:
            u = extract_link(columns[1])
            info[current_col].append(u)
        else:
            current_col = ''

    return info


def parse_data(data):
    for act_id, val in data.items():
        # if act_id != '78532':
        #     continue

        text = get_page('{}/{}'.format(BASE_URL, val['page']))
        try:
            info = extract_info(text)
            data[act_id].update(info)
        except Exception as ex:
            print("Could not extract for {}".format(act_id))
            raise ex


def build_data(law_type):
    data = {}
    for year in range(2007, 2021):
        url = '{}{}'.format(URLS[law_type], year)
        text = get_page(url)
        html = BeautifulSoup(text, 'html.parser')
        for link in html.find_all('a', href=True, ):
            href = link.get('href', '')
            url = urlparse(href)
            if url.path == 'legis_pck.htp_act':
                params = parse_qs(url.query)
                act_id = params.get('ida', [])[0]
                data[act_id] = {'page': href, 'year': year, 'type': REVERSE_TYPES[law_type]}
    return data


if __name__ == "__main__":
    data = build_data(TYPES['LEGE'])
    data1 = build_data(TYPES['OUG'])

    data.update(data1)

    parse_data(data)

    print(json.dumps(data))
