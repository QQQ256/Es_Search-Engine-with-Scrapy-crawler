import re

import scrapy
from ArticleSpider.utils import zhihu_login_sel
from ArticleSpider.settings import USER, PASSWORD
from urllib import parse
from scrapy.loader import ItemLoader
from ArticleSpider.items import ZhihuQuestionItem, ZhihuAnswerItem


class ZhihuSpider(scrapy.Spider):
    name = 'zhihu'
    allowed_domains = ['www.zhihu.com']
    start_urls = ['https://www.zhihu.com']
    start_answer_url = "https://www.zhihu.com/api/v4/answers/1461385376/concerned_upvoters?limit=10&offset=10"
    custom_settings = {
        "COOKIES_ENABLE": True
    }

    headers = {
        "HOST": "www.zhihu.com",
        "Referer": "https://www.zhizhu.com",
        'User-Agent': "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"
    }

    # def start_requests(self):
    #     # automatic mobile verification code to log in
    #     l = zhihu_login_sel.Login(USER, PASSWORD, 6)
    #     cookie_dict = l.login()
    #     for url in self.start_urls:
    #         headers = {
    #             'User-Agent': 'Mozilla/4.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
    #                           'Chrome/104.0.0.0 Safari/537.36 '
    #         }
    #         yield scrapy.Request(url, cookies=cookie_dict, headers=headers, dont_filter=True)

    def start_requests(self):

        import undetected_chromedriver as uc

        browser = uc.Chrome()
        # cnBlog's login link
        browser.get("https://www.zhihu.com/signin")
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

    def parse(self, response):
        """
        1. get all urls from one page and keep tracking on such urls
        2. if the format of the url is like: /question/xx, then go to the parse func after it's downloaded
        :param response:
        :return:
        """
        all_urls = response.css("a::attr(href)").extract()

        # the ulr we get does not have the domain(href=/question/xxx), use parse to solve it
        all_urls = [parse.urljoin(response.url, url) for url in all_urls]

        # use filter to dismiss wrong data
        all_urls = filter(lambda x: True if x.startswith("https") else False, all_urls)
        for url in all_urls:
            # use regular expression to get the right answer
            # 1. get id, 2. get full url
            # may end with pure id, or /answer/124364860; /answer is not needed
            match_obj = re.match("(.*zhihu.com/question/(\d+))(/|$).*", url)

            # if we get the question page, use parse_question
            # else we keep parsing the url
            if match_obj:
                request_url = match_obj.group(1)  # full link
                question_id = match_obj.group(2)  # (\d+)

                yield scrapy.Request(request_url, headers=self.headers, callback=self.parse_question,
                                     meta={"question_id": question_id})
            else:
                yield scrapy.Request(url, headers=self.headers, callback=self.parse)

    # handle question page, get question items from the page
    def parse_question(self, response):
        item_loader = ItemLoader(item=ZhihuQuestionItem(), response=response)
        item_loader.add_css("title", ".QuestionHeader-title::text")
        item_loader.add_css("content", ".css-eew49z span.RichText ztext css-yvdm7v p::text")
        item_loader.add_value("url", response.url)
        item_loader.add_value("zhihu_id", response.meta.get("question_id", []))
        item_loader.add_css("answer_num", ".List-headerText span::text")
        item_loader.add_css("comments_num", ".QuestionHeader-Comment button::text")
        item_loader.add_css("watch_user_num", ".NumberBoard-itemValue::text")   # 5 same divs, put them as a list
        item_loader.add_css("topics", ".QuestionHeader-topics .Popover div::text")

        question_item = item_loader.load_item()
        pass
