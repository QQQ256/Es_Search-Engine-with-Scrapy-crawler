import json
import redis
from django.shortcuts import render
from django.views.generic.base import View
from search.models import ArticleType
from django.http import HttpResponse
from elasticsearch import Elasticsearch
from datetime import datetime

client = Elasticsearch(hosts=["127.0.0.1"])
redis_cli = redis.StrictRedis("localhost")


# Create your views here.

class IndexView(View):
    # the top keyword is also shown on the main page

    def get(self, request):
        topN_search = redis_cli.zrevrangebyscore("search_keywords_set", "+inf", "-inf", start=0, num=5)
        return render(request, "index.html", {"topN_search": topN_search})


class SearchSuggest(View):
    def get(self, request):
        key_words = request.GET.get('s', '')  # url:suggest_url+"?s="
        re_datas = []
        if key_words:
            s = ArticleType.search()
            s = s.suggest('my_suggest', key_words, completion={
                "field": "suggest", "fuzzy": {
                    "fuzziness": 2
                },
                "size": 10
            })
            suggestions = s.execute_suggest()
            for match in suggestions.my_suggest[0].options:
                source = match._source
                re_datas.append(source["title"])

        return HttpResponse(json.dumps(re_datas), content_type="application/json")


class SearchView(View):
    def get(self, request):
        # window.location.href=search_url+'?q='+val+"&s_type="+$(".searchItem.current").attr('data-type')
        # get q as keyword!~
        key_words = request.GET.get('q', '')
        # the frequency of a key_word that's been searched, use redis func
        redis_cli.zincrby("search_keywords_set", 1, key_words)
        # use zrevrangebyscore to sort top 5 words that have high frequency
        topN_search = redis_cli.zrevrangebyscore("search_keywords_set", "+inf", "-inf", start=0, num=5)
        page = request.GET.get('p', "1")
        try:
            page = int(page)
        except:
            page = 1

        # get search time
        start_time = datetime.now()
        # use match method from elasticsearch (connect to local ES first!)
        response = client.search(
            index="cnblogs",
            body={
                "query": {
                    "multi_match": {
                        "query": key_words,
                        "fields": ["tags", "title", "content"]
                    }
                },
                # split pages
                "from": (page - 1) * 10,
                "size": 10,
                # highlight search words
                "highlight": {
                    # add custom html tags
                    "pre_tags": ['<span class="keyWord">'],
                    "post_tags": ['</span>'],
                    "fields": {
                        "title": {},
                        "content": {},
                        "tags": {}
                    }
                }
            }
        )

        end_time = datetime.now()
        used_search_time = (end_time - start_time).total_seconds()
        source = "cnblogs"
        cnbolg_count = redis_cli.get("jobbole_count")
        # get data from response and show them on html page
        total_nums = response["hits"]["total"]
        if page % 10 > 0:
            page_nums = int(total_nums / 10) + 1
        else:
            page_nums = int(total_nums / 10);
        # hits saved all info we need (dict type)
        hit_lists = []
        for hit in response["hits"]["hits"]:
            hit_dict = {}
            # titles&contents now are inside the highlight tags we defined early
            if "title" in hit["highlight"]:
                hit_dict["title"] = "".join(hit["highlight"]["title"])  # get the first array of the val
            else:
                hit_dict["title"] = hit["_source"]["title"]

            # contents are long, limit 500 for each
            if "content" in hit["highlight"]:
                hit_dict["content"] = "".join(hit["highlight"]["content"][:500])
            else:
                hit_dict["content"] = hit["_source"]["content"][:500]

            hit_dict["create_date"] = hit["_source"]["created_date"]
            hit_dict["url"] = hit["_source"]["url"]
            hit_dict["source"] = hit["_source"]
            hit_dict["score"] = hit["_score"]

            hit_lists.append(hit_dict)

        return render(request, "result.html", {"page": page,
                                               "all_hits": hit_lists,
                                               "key_words": key_words,
                                               "total_nums": total_nums,
                                               "page_nums": page_nums,
                                               "last_seconds": used_search_time,
                                               "cnblog_count": cnbolg_count,
                                               "topN_search": topN_search,
                                               "source": source})
