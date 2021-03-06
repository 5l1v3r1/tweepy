# from __future__ import absolute_import, print_function

# import pickle
# import pprint
# import json
# import string
import re

import tweepy
import nltk
import textblob
import pattern
import emoji
import operator

# import re
# import decimal`
# import MySQLdb

# from dateutil import parser
import sys

# Add the ptdraft folder path to the sys.path list
sys.path.append("/model")

from model import app_config
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from pattern.en import spelling

class TwitterClient(object):
    """
    Generic Twitter Class for sentiment analysis. s
    """

    def __init__(self):
        # keys and tokens from the Twitter Dev Console
        consumer_key = app_config.consumer_key
        consumer_secret = app_config.consumer_secret
        access_token = app_config.access_token
        access_token_secret = app_config.access_token_secret

        # attempt authentication
        try:
            # create OAuthHandler object
            self.auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
            # set access token and secret
            self.auth.set_access_token(access_token, access_token_secret)
            # create tweepy API object to fetch tweets
            self.api = tweepy.API(self.auth)
        except:
            print("Error: Authentication Failed")

        # == Database ==
        # HOST = app_config.HOST
        # USER = app_config.USER
        # PASSWD = app_config.PASSWD
        # DATABASE = app_config.DATABASE

    def reduce_lengthening(self, word):
        """
        remove repeated characters > 2
        ex: awwwwsome
        """
        pattern = re.compile(r"(.)\1{2,}")
        return pattern.sub(r"\1\1", word)

    def tokenizing_tweet(self, tweet):
        """
        Tokenization:
        Using regular expression mentioned below we will remove HTML Tags,
        @Mentions, Hash Tags, URLs and various other irrelevant terms that
        provide no value in our analysis
        """
        return re.sub("(@[A-Za-z0-9]+)|([^0-9A-Za-z \t])|(\w+:\/\/\S+)", " ", tweet.lower()).split()

    def clean_tweet(self, tweet):
        """
        Utility function to classify sentiment of passed tweet
        using textblob's sentiment method
        """
        # punctuation = list(string.punctuation)
        swords = set(stopwords.words("english"))
        ps = PorterStemmer()

        # Step 1 - emoji to text
        tweet = emoji.demojize(tweet)

        # Step 2 - tokenizing tweet - list
        tweet = self.tokenizing_tweet(tweet)

        # Step 3 - reduce length (ex: awwwwsome)
        tweet = [self.reduce_lengthening(term) for term in tweet]

        # Step 4 - remove stopwords then stemming word
        tweet = [ps.stem(term) for term in tweet if term not in set(swords)]

        return tweet

    def get_tweets(self, query, count=100, res_type="mixed"):
        """
        Main function to fetch tweets and parse them.
        """
        # empty list to store parsed tweets
        tweets = []
        counts = dict()

        try:
            # call twitter api to fetch tweets
            fetched_tweets = self.api.search(
                q=query, lang="en", result_type=res_type, count=count
            )

            # print(
            #     "[ Step 1 ] {0} <= Search [{1}] from twitter API".format(
            #         len(fetched_tweets), query
            #     )
            # )

            # parsing tweets one by one
            for tweet in fetched_tweets:
                # empty dictionary to store required params of a tweet
                parsed_tweet = {}

                # saving text of tweet
                try:
                    parsed_tweet["text"] = tweet.extended_tweet.full_text
                except AttributeError:
                    parsed_tweet["text"] = tweet.text


                cleaned_tweet = self.clean_tweet(parsed_tweet["text"])

                 # count word frequency
                for word in cleaned_tweet:
                    if word in counts:
                        counts[word] += 1
                    else:
                        counts[word] = 1

                # removing stopwords
                cleaned_tweet = " ".join(cleaned_tweet)

                # create TextBlob object of passed tweet text
                analysis = textblob.TextBlob(cleaned_tweet)

                # saving sentiment of tweet
                parsed_tweet["sentiment"] = analysis.sentiment.polarity

                # appending parsed tweet to tweets list
                if tweet.retweet_count > 0:
                    # if tweet has retweets, ensure that it is appended only once
                    if parsed_tweet not in tweets:
                        tweets.append(parsed_tweet)
                else:
                    tweets.append(parsed_tweet)

            # print("[ Step 2 ] {} <= unique tweets".format(len(tweets)))

            word_frequency = sorted(counts.items(),key=operator.itemgetter(1),reverse=True)

            # print(word_frequency)

            # return parsed tweets
            return (tweets, word_frequency)

        except tweepy.TweepError as e:
            # print error (if any)
            print("Error : " + str(e))


def search_tweet(search_query, limit, result_type="mixed", word_freq=25):
    # creating object of TwitterClient Class
    api = TwitterClient()
    # calling function to get tweets
    """
    - lang (en)
    - result_type (mixed recent popular):
        * mixed : Include both popular and real time results in the response.
        * recent : return only the most recent results in the response
        * popular : return only the most popular results in the response.
    """
    response = {}

    res = api.get_tweets(query=search_query, count=limit, res_type=result_type)
    tweets = res[0]
    word_frequency = res[1]
    total_count = len(tweets)

    # picking positive tweets from tweets
    ptweets = [tweet for tweet in tweets if tweet["sentiment"] > 0]
    p_count = len(ptweets)
    p_weight_sum = sum([t["sentiment"] for t in ptweets])
    p_percentage = 100.0 * p_count / total_count

    # picking negative tweets from tweets
    ntweets = [tweet for tweet in tweets if tweet["sentiment"] < 0]
    n_count = len(ntweets)
    n_weight_sum = sum([t["sentiment"] for t in ntweets])
    n_percentage = 100.0 * n_count / total_count

    # percentage of neutral tweets
    neu_count = total_count - p_count - n_count
    neu_percentage = 100.0 * neu_count / total_count

    # print("[ Result ] Positive : {} %  Weight: {}".format(p_percentage, p_weight_sum))
    # print("[ Result ] Negative : {} %  Weight: {}".format(n_percentage, n_weight_sum))
    # print("[ Result ] Neutral  : {} % ".format(neu_percentage))
    # print("[ Result ] Positive : {}".format(len(ptweets)))
    # print("[ Result ] Negative : {}".format(len(ntweets)))
    # print("[ Result ] Neutral  : {}".format(len(tweets) - len(ntweets) - len(ptweets)))
    # print("[ Result ] Total => : {}".format(len(tweets)))

    # printing first 5 positive tweets
    # print("\n\nPositive tweets:")
    # for tweet in ptweets[:5]:
    #     print(tweet["text"])

    # printing first 5 negative tweets
    # print("\n\nNegative tweets:")
    # for tweet in ntweets[:5]:
    #     print(tweet["text"])

    # return top xx freq word
    response['word_frequency'] = word_frequency[:word_freq]

    response['sentiment_analysis'] = dict({
        'counts': {
            'total': total_count,
            'positive': p_count,
            'negative': n_count,
            'neutral': neu_count,
        },
        'percentage': {
            'positive': p_percentage,
            'negative': n_percentage,
            'neutral': neu_percentage,
        }
    })

    response['tweets_data'] = dict({
        'positive_tweets': ptweets,
        'negative_tweets': ntweets,
    })

    return response



