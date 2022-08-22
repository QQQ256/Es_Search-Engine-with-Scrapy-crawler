from scrapy.cmdline import execute

import sys
import os

# 将这个文件目录加入python的path下
# sys这个的用处：将一个搜索目录加入python的目录之下
# dirname，找到这个文件的目录
if __name__ == '__main__':
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

    # crawl means start a spider
    execute(["scrapy", "crawl", "jobbole"])
