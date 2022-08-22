# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import codecs  # 处理文件的编码
import json
import pymysql

# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from scrapy.pipelines.images import ImagesPipeline
from scrapy.exporters import JsonItemExporter
from twisted.enterprise import adbapi
from w3lib.html import remove_tags


class ArticlespiderPipeline:
    def process_item(self, item, spider):
        return item


# 重载pipeline的方法定义保存路径和文件名称
class ArticleImagePipe(ImagesPipeline):
    # 来自imagepipe的方法
    def item_completed(self, results, item, info):
        if "front_image_url" in item:
            image_file_path = ""
            for ok, value in results:
                image_file_path = value["path"]
            item["front_image_path"] = image_file_path

        return item


# 使用自带的JsonItemExporter来将文件进行导出
class JsonExporterPipeline(object):
    # open files
    def __init__(self):
        # 打开文件，wb作为写入方法时，二进制方式打开
        self.file = open('articleExport.json', 'wb')
        self.exporter = JsonItemExporter(self.file, encoding="utf-8", ensure_ascii=False)
        self.exporter.start_exporting()

    # 参数和名称都不能错
    def process_item(self, item, spider):
        # 直接使用内置方法转换值
        self.exporter.export_item(item)
        return item

    # 参数和名称都不能错
    # 之后配置进settings
    def spider_closed(self, spider):
        self.exporter.finish_exporting()
        self.file.close()


class MysqlTwistedPipeline(object):
    def __init__(self, dbpool):
        self.dbpool = dbpool

    @classmethod
    def from_settings(cls, settings):
        from pymysql.cursors import DictCursor
        dbparams = dict(
            host=settings["MYSQL_HOST"],
            db=settings["MYSQL_DBNAME"],
            user=settings["MYSQL_USER"],
            passwd=settings["MYSQL_PASSWORD"],
            charset='utf8',
            cursorclass=pymysql.cursors.DictCursor,
            use_unicode=True
        )
        # 数据库异步的本质：使用twisted异步连接数据库而不是直接连接
        dbpool = adbapi.ConnectionPool("pymysql", **dbparams)
        return cls(dbpool)

    def process_item(self, item, spider):
        # 跑query语句，也就是插入数据的方法
        query = self.dbpool.runInteraction(self.do_insert, item)
        # 遇到错误，这里写个异步的方法捕捉，自定义的，参数是自己想要什么就写什么
        query.addErrback(self.handle_error, item, spider)
        return item

    def handle_error(self, failure, item, spider):
        print(failure)

    # 参数cursor自动注入
    def do_insert(self, cursor, item):
        # solve the primary key conflict problem with ON DUPLICATE KEY UPDATE
        insert_sql = """
                   insert into jobbole_article(title, url, url_object_id, front_image_path, front_image_url, praise_nums, comment_nums, fav_nums, tags,
                   content, create_date)
                   values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE praise_nums=VALUES(praise_nums)
               """
        params = list()
        params.append(item.get("title", ""))
        params.append(item.get("url", ""))
        params.append(item.get("url_object_id", ""))
        front_image_list = ",".join(
            item.get("front_image_path", []))  # there's no way to save list to MySQL, so we convert it with ','
        params.append(front_image_list)
        params.append(item.get("front_image_url", ""))
        params.append(item.get("praise_nums", 0))
        params.append(item.get("comment_nums", 0))
        params.append(item.get("fav_nums", 0))
        params.append(item.get("tags", ""))
        params.append(item.get("content", ""))
        params.append(item.get("create_date", "1970-07-01"))

        cursor.execute(insert_sql, tuple(params))
        return item


class ElasticsearchPipeline(object):
    # write data to Elasticsearch
    def process_item(self, item, spider):
        # run es_types again to refresh mapping
        item.save_to_es()

        return item

