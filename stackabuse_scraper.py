#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import json
import csv
import time
import logging
import pathlib
from slugify import slugify
from bs4 import BeautifulSoup
from argparse import ArgumentParser

BASE_URL = 'https://stackabuse.com'


def parse_page(page_url):
    '''Gets more data from the article page'''
    logging.info('Scraping {}'.format(page_url))
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
    }
    response = requests.get(page_url, headers=headers)
    if response is not None and response.status_code == 200:
        html = BeautifulSoup(response.content, 'html.parser')
        category_wrapper = html.find('div', {'class': 'mt-8 mb-4'})
        categories = map(lambda x: x.text.replace(
            '#', '').strip(), category_wrapper.find_all('a'))
        description_data = html.find_all(
            'meta', attrs={'name': 'description'})
        if len(description_data) > 0:
            description = description_data[0].get('content').strip()
        else:
            description = ''
        content = html.find_all('p')[0].text.strip()

        return {
            'categories': categories,
            'description': description,
            'content': content,
        }
    else:
        logging.error('Could not get a response for the link')
        return {}


def parse_posts(author_url, defaut_editor):
    '''Recursively retrieves all the posts of an blog write in stack abuse'''
    logging.info('Scraping {}'.format(author_url))
    posts = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
    }
    response = requests.get(author_url, headers=headers)
    if response is not None and response.status_code == 200:
        html = BeautifulSoup(response.content, 'html.parser')
        for article in html.find_all('div', {'class': 'p-6'}):
            article_details = article.find(
                'a', {'class': 'block hover:no-underline'})
            title = article_details.find('h3').text.strip()
            link = BASE_URL + article_details['href']
            meta = article.find('div', {'class': 'mt-6 flex items-center'})
            date_text = meta.find('time')['datetime'].strip()
            author_data = meta.find('a', {'class': 'hover:underline'})
            author = author_data.text.strip()

            time.sleep(0.5)
            page_data = parse_page(link)
            logging.debug(page_data)

            post = {
                'title': title,
                'link': link,
                'date': date_text,
                'author': author,
                'editor': defaut_editor,
                'description': page_data['description'],
                'categories': page_data['categories'],
                'content': page_data['content'],
            }

            posts.append(post)
        logging.info('{} posts found on page'.format(len(posts)))

        # Stack Abuse paginates every 9 posts, this collects the older ones
        pagination = html.find(
            'a', {'class': 'border-t-2 border-transparent pt-4 pl-1 inline-flex items-center text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300'})
        if pagination is not None:
            logging.info('Retrieving older posts')
            return posts + parse_posts(BASE_URL + pagination['href'], defaut_editor)
        return posts
    else:
        logging.error('Could not get a response for the link')
        return []


def get_posts_json(filename, author_url, defaut_editor):
    '''Dumps JSON for stack abuse articles'''
    posts = parse_posts(author_url, defaut_editor)
    logging.info('Retrieved {} posts'.format(len(posts)))
    with open(filename, 'w') as json_file:
        json.dump(posts, json_file, indent=4)


def get_posts_csv(filename, author_url, defaut_editor):
    '''Saves CSV file for stack abuse articles'''
    posts = parse_posts(author_url, defaut_editor)
    logging.info('Retrieved {} posts'.format(len(posts)))
    headers = ['Title', 'Link', 'Date']
    with open(filename, 'w') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=',', quoting=csv.QUOTE_ALL)
        csv_writer.writerow(headers)
        for post in posts:
            csv_writer.writerow([post['title'], post['link'], post['date']])


def get_posts_markdown(author_url, defaut_editor):
    '''Saves posts as markdown files to work in Hexo'''
    posts = parse_posts(author_url, defaut_editor)
    logging.info('Retrieved {} posts'.format(len(posts)))
    pathlib.Path('articles').mkdir(exist_ok=True)
    for post in posts:
        post_slug = slugify(post['title'])
        with open('articles/{}.md'.format(post_slug), 'w') as f:
            f.writelines([
                '---\n',
                'title: "{}"\n'.format(post['title']),
                'date: {}\n'.format(post['date']),
                'link: {}\n'.format(post['link']),
                'author: {}\n'.format(post['author']),
                'editor: {}\n'.format(post['editor']),
                'description'': "{}"\n'.format(post['description']),
                'tags'': [{}]\n'.format(', '.join(post['categories'])),
                '---\n\n',
                '{}\n'.format(post['content']),
            ])


def main():
    '''Argument parser for scraper'''
    parser = ArgumentParser(description='Web scraper for Stack Abuse writers')
    parser.add_argument('-a', '--author', dest='author',
                        help='Writer whose articles you want', required=True)

    parser.add_argument('-e', '--editor', dest='editor',
                        help='Editor for that author', required=True)

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--csv', action='store_true',
                       help='Save data in CSV format')
    group.add_argument('--json', action='store_true',
                       help='Save data in JSON format')
    group.add_argument('--markdown', action='store_true',
                       help='Save data as Markdown articles for Hexo')

    parser.add_argument('-l', '--loglevel', dest='loglevel',
                        help='Select log level', default='info')
    args = parser.parse_args()

    # Set logging preferences
    if args.loglevel == 'error':
        log_level = logging.ERROR
    elif args.loglevel == 'debug':
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig(filename='stackabuse_scraper.log', level=log_level)

    author_url = '{}/author/{}/'.format(BASE_URL, args.author)
    # Determine output format
    if args.csv:
        get_posts_csv('stackabuse_articles.csv', author_url, args.editor)
    elif args.json:
        get_posts_json('stackabuse_articles.json', author_url, args.editor)
    elif args.markdown:
        get_posts_markdown(author_url, args.editor)
    else:
        print(json.dumps(parse_posts(author_url)))


if __name__ == '__main__':
    main()
