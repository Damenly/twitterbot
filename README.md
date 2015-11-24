# Twitterbot
Twitterbot is a simple Python application for:
* reading and parsing a RSS feed and posting its title and links to a Twitter account.
* searching tweets for keywords or hashtags and retweet those tweets.

Both functions (Reading RSS and retweeting) can be used independently. The bot is limited to handle one feed and one Twitter account.

Please contact me at <a href="http://twitter.com/peterdalle">@peterdalle</a> if you have any questions.

## How do I install Twitterbot?

1. Download or git clone Twitterbot.
2. Create a <a href="https://apps.twitter.com/">Twitter application</a>, and access tokens and keys.
3. Install the dependencies (<a href="https://pythonhosted.org/feedparser/">feedparser</a> and <a href="https://twython.readthedocs.org/en/latest/">twython</a>):
   <code>pip install feedparser</code>
   <code>pip install twython</code>
4. Modifiy the settings in the source code.
   - Modify <code>FeedUrl</code> to the RSS feed you want to read.
   - Modify the variables in the <code>TwitterAuth</code> class and add the access tokens and keys for connecting to Twitter.
   - Modify <code>include_words</code> for keywords you want to search for, and <code>exclude_words</code> for keywords you would like to exclude. For example <code>include_words = ["foo"]</code> and <code>exclude_words = ["bar"]</code> will include any tweet with the word "foo", as long as the word "bar" is absent.

## How do I use Twitterbot?

Read the RSS feed and post to account:

<code>$ python medieforskarna.py rss</code>

For example, if you would like to retweet every hour:

<code>$ python medieforskarna.py rt</code>

Preferably, you should use crontab to set it up to run once every hour or so.
