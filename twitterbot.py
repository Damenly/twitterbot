#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import feedparser
import tweepy
import re
import urllib
import time
import tempfile
import configparser

def strip_message(message):
    message = message.replace('转发', '//')
    message = message.replace('回复@', '回复ⓐ')
    message = message.replace('@', 'ⓐ')
    message = message.replace('// ', '//')
    message = message.replace(' //', '//')
    message = message.replace('////', '//')
    
    if len(message) >= 210:
                message = message[0:210]
    return message

def striphtml(data):
    p = re.compile(r'<.*?>')
    return p.sub('', data)

class Settings:
    """Twitter bot application settings.

    Enter the RSS feed you want to tweet, or keywords you want to retweet.
    """
    # RSS feed to read and post tweets from.
    feeds = ["https://damenly.herokuapp.com/rss/2681602924",
             "https://rssfeed.today/weibo/rss/2681602924"]

    config_path = "/etc/wb2twitter.ini"

    # Log file to save all tweeted RSS links (one URL per line).
    posted_urls_output_file = "/usr/local/posted-urls.log"

    # Log file to save all retweeted tweets (one tweetid per line).
    posted_retweets_output_file = "/usr/local/posted-retweets.log"

    # Include tweets with these words when retweeting.
    retweet_include_words = ["#hashtag"]

    # Do not include tweets with these words when retweeting.
    retweet_exclude_words = []

    max_weibo_count = 10

    post_interval = 1200

    feed_retry_interval = 60

class TwitterAuth:
    """Twitter authentication settings.

    Create a Twitter app at https://apps.twitter.com/ and generate
    consumer key, consumer secret etc. and insert them here.
    """
    consumer_key = ""
    consumer_secret = ""
    access_token = ""
    access_token_secret = ""

    def init():
        if not os.path.exists(Settings.config_path):
            print(Settings.config_path + "is not existed")
            sys.exit(1)

        config = configparser.ConfigParser()

        try:
            config.read(Settings.config_path)
            TwitterAuth.consumer_key = config["tokens"]["consumer_key"]
            TwitterAuth.consumer_secret = config["tokens"]["consumer_secret"]
            TwitterAuth.access_token = config["tokens"]["access_token"]
            TwitterAuth.access_token_secret = config["tokens"]["access_token_secret"]

            Settings.max_weibo_count = int(config["limits"]["max_weibo_count"])
            Settings.feed_retry_interval = int(config["limits"]["feed_retry_interval"])
            Settings.post_interval = int(config["limits"]["post_interval"])
        except Exception as e:
            print("Can not initilize config")
            sys.exit(1)

def compose_message(item: feedparser.FeedParserDict) -> str:
    """Compose a tweet from an RSS item (title, link, description)
    and return final tweet message.

    Parameters
    ----------
    item: feedparser.FeedParserDict
        An RSS item.

    Returns
    -------
    str
        Returns a message suited for a Twitter status update.
    """
    title, link, _ = item["title"], item["link"], item["description"]
    message = shorten_text(title, maxlength=250) + " " + link
    return message


def shorten_text(text: str, maxlength: int) -> str:
    """Truncate text and append three dots (...) at the end if length exceeds
    maxlength chars.

    Parameters
    ----------
    text: str
        The text you want to shorten.
    maxlength: int
        The maximum character length of the text string.

    Returns
    -------
    str
        Returns a shortened text string.
    """
    return (text[:maxlength] + '...') if len(text) > maxlength else text


def post_tweet_plain_text(message: str):
    """Post tweet message to account.

    Parameters
    ----------
    message: str
        Message to post on Twitter.
    """
    try:
        auth = tweepy.OAuthHandler(TwitterAuth.consumer_key, TwitterAuth.consumer_secret)
        auth.set_access_token( TwitterAuth.access_token, TwitterAuth.access_token_secret)
        api = tweepy.API(auth)

        api.update_status(message)
    except Exception as e:
        print(e)

def post_tweet_with_images(message: str, files):
    """Post tweet message to account.

    Parameters
    ----------
    message: str
        Message to post on Twitter.
    """
    try:
        auth = tweepy.OAuthHandler(TwitterAuth.consumer_key, TwitterAuth.consumer_secret)
        auth.set_access_token( TwitterAuth.access_token, TwitterAuth.access_token_secret)
        api = tweepy.API(auth)
        api.update_status(status=message, media_ids=upload_imgs(api, files))

    except Exception as e:
        print(e)

def download_images(dir, urls):
    files = []
    try:
        for url in urls:
            name =  dir + "/" + url.rsplit('/', 1)[-1]
            urllib.request.urlretrieve(url, name)
            files.append(name)

    except Exception as e:
        print(e)
        return []
    return files

def upload_imgs(api, files):
    media_ids = []
    for f in files:
        res = api.media_upload(f)
        media_ids.append(res.media_id)
    return media_ids

def read_rss_and_tweet(url: str):
    """Read RSS and post feed items as a tweet.

    Parameters
    ----------
    url: str
        URL to RSS feed.
    """
    feed = feedparser.parse(url)
    if feed:
        feed["items"].reverse()
        items = feed["items"]
        for item in items:
            print(item)
            refs = re.findall(r'(https?://[^\s]+)', item["description"])
            #print(refs)
            images = []
            for ref in refs:
                ref = ref.replace('"', '')
                ref = ref.replace("'", '')
                #print(ref)
                if ref.endswith(".jpg") or ref.endswith(".gif"):
                    images.append(ref.replace('https', 'http'))
            images = list(set(images))
            if item["description"].find("video") != -1:
                continue
            message = striphtml(item["description"])
            print(message)
            r1 = message.find('转发')
            if r1 == -1:
                r1 = 65536
            r2 = message.find('@')
            if r2 == -1:
                r2 = 65536
            if r1 != 65536 or r2 != 65536:
                if r1 < r2:
                    min = r1
                else:
                    min = r2
                if min == r1:
                    message = message[:min] + "//" + message[min + 2:]
                elif min - 1 >= 0 and message[min - 1] != '/':
                        message = message[:min] + "//" + message[min:]
            #print("\t", striphtml(item["description"]), item["link"], "\n")
            #continue
            link = item["link"]
            if is_in_logfile(link, Settings.posted_urls_output_file):
                print("Already posted:", link)
                continue
            else:
                if len(images) == 0:
                    post_tweet_plain_text(message)
                else:
                    i = 0
                    while i < len(images):
                        count = 4
                        while i < len(images) and count > 0:
                            i = i + 1
                            count = count - 1
                        if i >= 4:
                            if i != 4:
                                message = '接上条'
                            if i == 4:
                                _images = images[i - 4:i]
                            else:
                                if i % 4 == 0:
                                    _images = images[i - 4:i]
                                else:
                                    _images = images[i - i % 4 : i]
                        else:
                            _images = images
                        message = strip_message(message)
                        print("image index: ", i, "len: ", len(_images))
                        print(message, images, "message len:", len(message))

                        with tempfile.TemporaryDirectory() as tmpdirname:
                            files = download_images(tmpdirname, _images)
                            post_tweet_with_images(message, files)

                        print("Posted:", link)
                        time.sleep(60)

                write_to_logfile(link, Settings.posted_urls_output_file)
                time.sleep(60)

    else:
        print("Nothing found in feed", url)


def get_query() -> str:
    """Create Twitter search query with included words minus the
    excluded words.

    Returns
    -------
    str
        Returns a string with the Twitter search query.
    """
    include = " OR ".join(Settings.retweet_include_words)
    exclude = " -".join(Settings.retweet_exclude_words)
    exclude = "-" + exclude if exclude else ""
    return include + " " + exclude


def search_and_retweet(query: str, count=10):
    """Search for a query in tweets, and retweet those tweets.

    Parameters
    ----------
    query: str
        A query to search for on Twitter.
    count: int
        Number of tweets to search for. You should probably keep this low
        when you use search_and_retweet() on a schedule (e.g. cronjob).
    """
    try:
        twitter = Twython(TwitterAuth.consumer_key,
                          TwitterAuth.consumer_secret,
                          TwitterAuth.access_token,
                          TwitterAuth.access_token_secret)
        search_results = twitter.search(q=query, count=count)
    except TwythonError as e:
        print(e)
        return
    for tweet in search_results["statuses"]:
        # Make sure we don't retweet any dubplicates.
        if not is_in_logfile(
                    tweet["id_str"], Settings.posted_retweets_output_file):
            try:
                twitter.retweet(id=tweet["id_str"])
                write_to_logfile(
                    tweet["id_str"], Settings.posted_retweets_output_file)
                print("Retweeted {} (id {})".format(shorten_text(
                    tweet["text"], maxlength=40), tweet["id_str"]))
            except TwythonError as e:
                print(e)
        else:
            print("Already retweeted {} (id {})".format(
                shorten_text(tweet["text"], maxlength=40), tweet["id_str"]))

def cleanup_logfile(file):
    with open(file, "r") as f:
            lines = f.readlines()

    if len(lines) > Settings.max_weibo_count:
        lines_to_delete = len(lines) - Settings.max_weibo_count

        with open(file, "w") as f:
            f.writelines(lines[:-lines_to_delete])

def is_in_logfile(content: str, filename: str) -> bool:
    """Does the content exist on any line in the log file?

    Parameters
    ----------
    content: str
        Content to search file for.
    filename: str
        Full path to file to search.

    Returns
    -------
    bool
        Returns `True` if content is found in file, otherwise `False`.
    """
    if os.path.isfile(filename):
        with open(filename) as f:
            lines = f.readlines()
        if (content + "\n" or content) in lines:
            return True
    return False


def write_to_logfile(content: str, filename: str):
    """Append content to log file, on one line.

    Parameters
    ----------
    content: str
        Content to append to file.
    filename: str
        Full path to file that should be appended.
    """
    try:
        with open(filename, "a") as f:
            f.write(content + "\n")
    except IOError as e:
        print(e)


def display_help():
    """Show available commands."""
    print("Syntax: python {} [command]".format(sys.argv[0]))
    print()
    print(" Commands:")
    print("    rss    Read URL and post new items to Twitter")
    print("    rt     Search and retweet keywords")
    print("    help   Show this help screen")


if __name__ == "__main__":
    TwitterAuth.init()

    while True:
        cleanup_logfile(Settings.posted_urls_output_file)
        for feed_url in Settings.feeds:
            read_rss_and_tweet(url=feed_url)
            time.sleep( Settings.feed_retry_interval )
        time.sleep( Settings.post_interval )
