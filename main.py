import json
import requests
from bs4 import BeautifulSoup
import os
import pickle

from geopy.distance import geodesic

headers = {"accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
           "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/112.0"}


def get_all_drugs(url):
    if os.path.exists("my_dict.pickle"):
        with open("my_dict.pickle", "rb") as f:
            drugs_dict = pickle.load(f)
    else:
        s = requests.Session()
        response = s.get(url=url, headers=headers)

        soup = BeautifulSoup(response.text, "html.parser")
        notes = str(soup.select('.list'))

        drugs_dict = {}
        soup = BeautifulSoup(notes, 'html.parser')
        for link in soup.find_all('a'):
            drugs_dict.update({link.text: link.get('href').split('/')[3]})
        with open("my_dict.pickle", "wb") as f:
            pickle.dump(drugs_dict, f)
    return drugs_dict


def get_drug(url, drug):
    s = requests.Session()
    response = s.get(url=url, headers=headers)

    soup = BeautifulSoup(response.text, "html.parser")
    notes = str(soup.select('.drugsForm__item-buttons'))

    drug_dict = {}
    soup = BeautifulSoup(notes, 'html.parser')
    for link in soup.find_all('a'):
        drug_list = link.get('href').split('/')
        if drug_list[1] == drug:
            drug_dict.update({drug_list[2]: drug_list[2] + '/' + drug_list[3]})
    return drug_dict


def get_number_drug(url):
    s = requests.Session()
    response = s.get(url=url, headers=headers)

    soup = BeautifulSoup(response.text, "html.parser")
    notes = soup.find('label', {'class': 'bookmark__toggleFavorite'})
    return notes['data-id']


def get_list_drug(url):
    s = requests.Session()
    response = s.get(url=url, headers=headers)
    data = response.json()

    shop_dict = {}
    for drug in data.get('data'):
        shop_dict.update({drug.get('i'): drug.get('p')})
    return list(shop_dict.items())


def get_more_info(shop_dict, id_drug, loc):
    s = requests.Session()

    result = []
    for value in shop_dict:
        response = s.get(url=f"https://apteka.103.by/api/v2/pharmacy/{value[0]}/?sku_id={id_drug}", headers=headers)
        data = response.json()
        value_name = data['data']['name']
        value_phone = data['data']['phones']
        value_address = data['data']['address'].replace('"', "'")
        value_price = data['data']['offers']['items'][0]['price']
        value_location = (data['data']['location']['lat'], data['data']['location']['lon'])
        if loc is not None:
            distance = geodesic((loc['latitude'], loc['longitude']), value_location).km
            result.append({'name': value_name, 'price': value_price, 'address': value_address, 'phone': value_phone[0],
                           'distance': distance})
        else:
            result.append({'name': value_name, 'price': value_price, 'address': value_address, 'phone': value_phone[0]})

    return result
