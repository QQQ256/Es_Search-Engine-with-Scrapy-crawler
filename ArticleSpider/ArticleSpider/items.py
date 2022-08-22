# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
import re
import redis
from scrapy.loader.processors import MapCompose, TakeFirst, Identity, Join
from scrapy.loader import ItemLoader
from w3lib.html import remove_tags
from .models.es_types import ArticleType
from elasticsearch_dsl.connections import connections
es = connections.create_connection(ArticleType._doc_type.using)

# add data quantity to redis
redis_cli = redis.StrictRedis(host="localhost")

class ArticlespiderItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass


# 对所有的output_processor采取统一的TakeFirst()
# 自定义ItemLoader
class ArticleItemLoader(ItemLoader):
    default_output_processor = TakeFirst()


def date_convert(value):  # value 自动传递进来
    match_re = re.match(".*?(\d+.*)", value)
    if (match_re):
        return match_re.group(1)
    else:
        return "1900-00-00"


# generate suggestion arrays based on the input string
def gen_suggest_pool(index, info_tuple):
    # dismiss data that fits the suggestion but from other parts like tags, content
    used_words = set()
    suggests = []
    for text, weight in info_tuple:
        if text:
            # call es analyzer interface to analyze input strings
            words = es.indices.analyze(index=index, analyzer="ik_max_word", params={'filter': ["lowercase"]}, body=text)
            analyzed_words = set([r["token"] for r in words["tokens"] if (len(r["token"]) > 1)])
            new_words = analyzed_words - used_words  # 差：取一个集合中另一个集合没有的元素
        else:
            new_words = set()

        if new_words:
            suggests.append({"input": list(new_words), "weight": weight})  # the format shoudld be [{"input": [],
            # "weight": 2}]
    return suggests


class JobBoleArticleItem(scrapy.Item):
    title = scrapy.Field()
    created_date = scrapy.Field(
        input_processor=MapCompose(date_convert)  # 做正则表达式的提取
    )
    url = scrapy.Field()
    url_object_id = scrapy.Field()
    front_image_url = scrapy.Field(
        output_processor=Identity()  # output为takeFirst会将所有的值段变成str，然鹅img要下载，必须是保持之前的url状态，这里将output设置为Identity()保持不变
    )
    front_image_path = scrapy.Field()
    praise_nums = scrapy.Field()
    comment_nums = scrapy.Field()
    view_nums = scrapy.Field()
    tags = scrapy.Field(
        output_processor=Join(separator=",")  # tags是list，用，隔开
    )
    content = scrapy.Field()

    def save_to_es(self):
        # convert item to es data type
        from .models.es_types import ArticleType
        # now we can operate the ArticleType as an object
        article = ArticleType()
        article.title = self['title']
        article.created_date = self['created_date']
        article.content = remove_tags(self["content"])
        article.front_image_url = self['front_image_url']
        if 'front_image_path' in self:
            article.front_image_path = self['front_image_path']
        article.praise_nums = self['praise_nums']
        article.comment_nums = self['comment_nums']
        article.view_nums = self['view_nums']
        article.url = self['url']
        if 'tags' in self:
            article.tags = self["tags"]
        article.url_object_id = self['url_object_id']

        # build search suggestion pool
        # article.suggest = [{"input": [], "weight": 2}]
        article.suggest = gen_suggest_pool(ArticleType._doc_type.index, ((article.title, 10), (article.tags, 7)))

        article.save()
        redis_cli.incr("jobbole_count")

class ZhihuQuestionItem(scrapy.Item):
    # ItemLoader for question item
    zhihu_id = scrapy.Field()
    topics = scrapy.Field()
    url = scrapy.Field()
    title = scrapy.Field()
    content = scrapy.Field()
    answer_num = scrapy.Field()
    comments_num = scrapy.Field()
    watch_user_num = scrapy.Field()
    click_num = scrapy.Field()
    crawl_time = scrapy.Field()


class ZhihuAnswerItem(scrapy.Item):
    zhihu_id = scrapy.Field()
    url = scrapy.Field()
    question_id = scrapy.Field()
    author_id = scrapy.Field()
    content = scrapy.Field()
    praise_num = scrapy.Field()
    comments_num = scrapy.Field()
    create_time = scrapy.Field()
    update_time = scrapy.Field()
    crawl_time = scrapy.Field()
