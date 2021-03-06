# -*- coding: utf-8 -*-

import redis  # pylint: disable=E0401
import hashlib
import datetime

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'common'))

import news_api_client   # pylint: disable=E0401
from cloudAMQP_client import CloudAMQPClient   # pylint: disable=E0401

from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

MQ_SCRAPE_NEWS_QUEUE_HOST = os.environ.get("MQ_SCRAPE_NEWS_QUEUE_HOST")
MQ_SCRAPE_NEWS_QUEUE_NAME = os.environ.get("MQ_SCRAPE_NEWS_QUEUE_NAME")

DB_CACHE_REDIS_HOST = os.environ.get("DB_CACHE_REDIS_HOST")
DB_CACHE_REDIS_PORT = os.environ.get("DB_CACHE_REDIS_PORT")

SLEEP_TIME_IN_SECONDS = 60 * 60
NEWS_TIME_OUT_IN_SECONDS = 3600 * 24 * 3

NEWS_SOURCES = {
    'bbc-news',
    'bbc-sport',
    'bloomberg',
    'cnn',
    'entertainment-weekly',
    'espn',
    'ign',
    'techcrunch',
    'the-new-york-times',
    'the-wall-street-journal',
    'the-washington-post'
}

redis_client = redis.StrictRedis(DB_CACHE_REDIS_HOST, DB_CACHE_REDIS_PORT)
cloudAMQP_client = CloudAMQPClient(
    MQ_SCRAPE_NEWS_QUEUE_HOST, MQ_SCRAPE_NEWS_QUEUE_NAME)


def run():
    while True:
        news_list = news_api_client.getNewsListFromSources(NEWS_SOURCES)
        num_of_new_news = 0

        for news in news_list:
            news_digest = hashlib.md5(
                news['title'].encode('utf-8')).hexdigest()

            if redis_client.get(news_digest) is None:
                num_of_new_news += 1
                news['digest'] = news_digest

                if news['publishedAt'] is None:
                    news['publishedAt'] == datetime.datetime.utcnow().strftime(
                        "%Y-%m-%dT%H:%M:%SZ")

                redis_client.set(news_digest, 'True')
                redis_client.expire(news_digest, NEWS_TIME_OUT_IN_SECONDS)

                cloudAMQP_client.sendMessage(news)

        print("Fetched %d news." % num_of_new_news)

        cloudAMQP_client.sleep(SLEEP_TIME_IN_SECONDS)


if __name__ == '__main__':
    run()
