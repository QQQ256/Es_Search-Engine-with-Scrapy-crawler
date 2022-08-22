import scrapy
from datetime import datetime
from elasticsearch_dsl import DocType, Date, Nested, Boolean, \
    analyzer, InnerObjectWrapper, Completion, Keyword, Text, Integer
from elasticsearch_dsl.analysis import CustomAnalyzer as _CustomAnalyzer
from scrapy.loader.processors import MapCompose, TakeFirst, Identity, Join
from collections.abc import Mapping
from elasticsearch_dsl.connections import connections
connections.create_connection(hosts=["localhost"])


# fix the bug from es
class CustomerAnalyzer(_CustomAnalyzer):
    def get_analysis_definition(self):
        return {}


ik_analyzer = CustomerAnalyzer("ik_max_word", filter=['lowercase'])


class ArticleType(DocType):
    # the type from cnblogs
    # we use type in es to replace values

    # add suggestor to the article
    suggest = Completion(analyzer=ik_analyzer)
    title = Text(
        # define analyzer
        analyzer="ik_max_word"
    )
    created_date = Date()
    url = Keyword()
    url_object_id = Keyword()
    front_image_url = Keyword()
    front_image_path = Keyword()
    praise_nums = Integer()
    comment_nums = Integer()
    view_nums = Integer()
    tags = Text(analyzer="ik_max_word")
    content = Text(analyzer="ik_max_word")

    # the init data of the ArticleType
    class Meta:
        index = "cnblogs"
        doc_type = "article"


if __name__ == "__main__":
    ArticleType.init()  # instantiate mapping based on ArticleType
