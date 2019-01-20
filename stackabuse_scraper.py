#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import json
import csv
import datetime
import logging
from bs4 import BeautifulSoup

logging.basicConfig(filename='scraper.log',level=logging.INFO)
BASE_URL = 'https://stackabuse.com'

def parse_posts(author_url):
    '''Recursively retrieves all the posts of an blog write in stack abuse'''
    logging.info('Scraping {}'.format(author_url))
    posts = []
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'}
    response = requests.get(author_url, headers=headers)
    if response is not None and response.status_code == 200:
        html = BeautifulSoup(response.content, 'html.parser')
        for article in html.select('article'):
            title_tag = article.find('h2', {'class': 'post-title'}).find('a')
            title = title_tag.text
            link = BASE_URL + title_tag['href']
            meta = article.find('div', {'class': 'post-meta'})
            date_text = meta.find('span', {'class': 'date'}).text
            date = datetime.datetime.strptime(date_text, '%B %d, %Y')
            post = {
                'title': title,
                'link': link,
                'date': datetime.date.strftime(date, "%Y-%m-%d"),
            }
            posts.append(post)
        logging.info('{} posts found on page'.format(len(posts)))
        # Stack Abuse paginates every 5 posts, this collects the older ones
        pagination = html.find('nav', {'class': 'pagination'}).find('a', {'class': 'older-posts'})
        if pagination is not None:
            logging.info('Retrieving older posts')
            return posts + parse_posts(BASE_URL + pagination['href'])
        return posts
    else:
        logging.error('Could not get a response for the link')
        return []


def get_posts_json(filename, author_url):
    '''Dumps JSON for stack abuse articles'''
    posts = parse_posts(author_url)
    logging.info('Retrieved {} posts'.format(len(posts)))
    with open(filename, 'w') as json_file:
        json.dump(posts, json_file, indent=4)


def get_posts_csv(filename, author_url):
    '''Saves CSV file for stack abuse articles'''
    posts = parse_posts(author_url)
    logging.info('Retrieved {} posts'.format(len(posts)))
    headers = ['Title', 'Link', 'Date']
    with open(filename, 'w') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=',', quoting=csv.QUOTE_ALL)
        csv_writer.writerow(headers)
        for post in posts:
            csv_writer.writerow([post['title'], post['link'], post['date']])


if __name__ == '__main__':
    get_posts_csv('stackabuse_articles.csv', BASE_URL + '/author/usman/')
