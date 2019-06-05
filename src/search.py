import os
import requests
from requests.auth import HTTPBasicAuth
from filter import Filter
from setting import GEOM_USER_METHOD, SAVED_SEARCH_ID

class Search:
    """
    数据检索类
    """
    # requests HTTP请求会话初始化
    _session = requests.Session()
    _session.auth = HTTPBasicAuth('85a26a7cda5f427dab336c2832e7e7b7', '')
    # 定义查询返回结果的列表容器
    itemList = [] #查询到的item列表

    def _createSearch(self):
        """
        创建saved search
        :return string saved_search的id
        """
        filterObj = Filter()
        # 一个saved search请求体
        search_body = {
        "item_types": ["Landsat8L1G", "Sentinel2L1C"],
        "filter": filterObj.filterGenerator(GEOM_USER_METHOD),
        "name": 'wenchang'
        }
        # 执行saved search的POST请求
        saved_search = \
        self._session.post(
            'https://api.planet.com/data/v1/searches',
            json=search_body)
        if saved_search.status_code == 403:
            print("抱歉！无访问权限，正在退出！")
            exit(0)
        else:
            return saved_search.json()["id"]

    def runSearch(self):
        """
        运行saved search
        """
        # 取得saved search的id
        saved_search_id = ''
        if SAVED_SEARCH_ID == '': #没有保存saved_search_id就创建
            saved_search_id = self._createSearch()
        else: #保存了saved_search_id就直接取用
            saved_search_id = SAVED_SEARCH_ID
        # 发起请求，同时对请求结果Paginate
        ## 定义paginate初始的格式
        page_size = 10 # 定义每页的item个数
        first_page =  \
            "https://api.planet.com/data/v1/searches/{}/results?_page_size={}".format(saved_search_id, page_size)
        ## 递归执行paginate
        self._fetch_page(first_page)

    def _fetch_page(self, search_url):
        """
        定义实现paginate请求的递归函数
        """
        page = self._session.get(search_url).json()
        if page:
            self._handle_page(page)
        next_url =  page["_links"].get("_next")
        if next_url:
            self._fetch_page(next_url)

    def _handle_page(self, page):
        """
        对于每一页，定义执行内容的函数实现
        """
        for item in page['features']:
            self.itemList.append(item)

