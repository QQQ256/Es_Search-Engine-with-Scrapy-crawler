import re
from multiprocessing import freeze_support
import urllib
from urllib import parse
from urllib.request import Request

import scrapy
import requests
import json

from ArticleSpider.items import JobBoleArticleItem
from ArticleSpider.utils import common
from ArticleSpider.items import ArticleItemLoader  # 使用自己的ItemLoader


class JobboleSpider(scrapy.Spider):
    name = 'jobbole'
    allowed_domains = ['news.cnblogs.com']
    start_urls = ['https://news.cnblogs.com/']
    custom_settings = {
        "COOKIES_ENABLE": True
    }

    # Simulate login
    def start_requests(self):

        import undetected_chromedriver as uc

        browser = uc.Chrome()
        # cnBlog's login link
        browser.get("https://account.cnblogs.com/signin")
        input("input enter to continue")
        cookies = browser.get_cookies()
        cookie_dict = {}
        for cookie in cookies:
            cookie_dict[cookie['name']] = cookie['value']

        for url in self.start_urls:
            # Give the cookie directly to scrapy,
            # will subsequent requests use the previously requested cookie? No, scrapy will be closed
            headers = {
                'User-Agent': 'Mozilla/4.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36'
            }
            yield scrapy.Request(url, cookies=cookie_dict, headers=headers, dont_filter=True)

    # pase is use for writing parsing strategies
    def parse(self, response):
        """
        1. get urls from the news list, put urls to scrapy request to download and use callback methods
        2. get urls from the next page and give it to scrapy to download; after downloaded, call parse to continue
        """

        post_nodes = response.css('#news_list .news_block')
        for post_node in post_nodes:
            image_url = post_node.css('.entry_summary a img::attr(src)').extract_first("")
            if image_url.startswith("//"):
                image_url = "https:" + image_url
            post_url = post_node.css('h2 a::attr(href)').extract_first("")

            yield scrapy.Request(url=parse.urljoin(response.url, post_url), meta={"front_image_url": image_url},
                                 callback=self.parse_detail)
            # break

        # Extract the next page and hand it to scrapy to download
        # # xpath or css extractor
        # # next_url = response.xpath("//a[contains(text(), 'Next >')/@href]")
        next_url = response.css('div.pager a:last-child::text').extract_first("")

        if next_url == "Next >":
            next_url = response.css('div.pager a:last-child::attr(href)').extract_first("")
            yield scrapy.Request(url=parse.urljoin(response.url, next_url), callback=self.parse)

    def parse_detail(self, response):

        # The content of the value cannot be obtained from the html side, they are obtained through js code,
        # or from the server through GET Since the value taken is in JSON format, you can use the code in the
        # requests package to decode JSON and get the required value (provided that the corresponding GET link is
        # found) Get the id at the end of the url, which is the ID of each detailed page use regular expressions
        match_re = re.match(".*?(\d+)", response.url)
        # To improve the meticulousness of logic,
        # there must be an id that matches to the end before crawling the content in html
        if match_re:
            post_id = match_re.group(1)

            item_loader = ArticleItemLoader(item=JobBoleArticleItem(), response=response)

            item_loader.add_css("title", "#news_title a::text")
            item_loader.add_css("content", "#news_content")
            item_loader.add_css("tags", ".news_tag a::text")
            item_loader.add_css("created_date", "#news_info span.time::text")
            item_loader.add_value("url", response.url)
            if response.meta.get("front_image_url", []):
                item_loader.add_value("front_image_url", response.meta.get("front_image_url", []))

            # article_item = item_loader.load_item()

            url = parse.urljoin(response.url, "/NewsAjax/GetAjaxNewsInfo?contentId={}".format(post_id))
            yield scrapy.Request(
                url=url,
                meta={"article_item": item_loader, "url": response.url},
                callback=self.parse_nums)

    @staticmethod
    def parse_nums(response):
        j_data = json.loads(response.text)

        item_loader = response.meta.get("article_item", "")
        item_loader.add_value("praise_nums", j_data["DiggCount"])
        item_loader.add_value("view_nums", j_data["TotalView"])
        item_loader.add_value("comment_nums", j_data["CommentCount"])
        item_loader.add_value("url_object_id", common.get_md5(response.meta.get("url", "")))

        article_item = item_loader.load_item()

        yield article_item
