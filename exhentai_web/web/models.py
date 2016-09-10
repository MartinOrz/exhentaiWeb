# coding=utf-8
from django.db import models


# 一些常量定义 ===========================================================================================================
# 画集类型
types = {
    'doujinshi': 1,
    'manga': 2,
    'artistcg': 3,
    'gamecg': 4,
    'western': 5,
    'non-h': 6,
    'imageset': 7,
    'cosplay': 8,
    'asianporn': 9,
    'misc': 10,
}

# 语言
languages = {
    'Japanese': 1,
    'Chinese': 2,
    'English': 3,
    'Korean': 4,
    'Spanish': 5,
    'Russian': 6,
    'French': 7,
    'Thai': 8,
    'Polish': 9,
    'Other': 10
}

# 画集状态
status = {
    'not_downloaded': 0,
    'downloaded': 1,
    'deleted': 2,
}

DEFAULT_STATUS = 'downloaded'

# 评分
DEFAULT_RATING = 50


class ExGallery(models.Model):
    """
    用于存储的画集实体类
    """
    id = models.IntegerField(primary_key=True)
    root_path = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    name_n = models.CharField(max_length=255)
    name_j = models.CharField(max_length=255)
    type = models.IntegerField()
    language = models.IntegerField()
    translator = models.CharField(max_length=255)
    pages = models.IntegerField()
    length = models.IntegerField()
    posted = models.DateTimeField()
    is_anthology = models.IntegerField()
    rating = models.IntegerField()
    status = models.IntegerField()
    last_view = models.DateTimeField()

    @staticmethod
    def get_object(dic):
        """
        从gallery.pkl中解析内容，生成一个ExGallery对象

        :param dic: 需要解析的字典
        :return: 解析出的ExGallery对象，如果dic为None，则返回None
        """
        if not dic:
            return None

        result = ExGallery()
        root_path = dic['root_path']
        result.id = int(root_path.split('/')[4])
        result.root_path = root_path
        result.name = dic['name']
        result.name_n = dic['name_n']
        result.name_j = dic['name_j']
        result.type = types[dic['type']]
        result.language = languages[dic['language']]
        result.translator = dic['translator']
        result.pages = dic['pages']
        result.length = dic['length']
        result.posted = dic['posted']
        result.is_anthology = 1 if dic['is_anthology'] else 0
        result.rating = DEFAULT_RATING = 50
        result.status = status[DEFAULT_STATUS]
        result.last_view = '2016-01-01 00:00:00'
        return result
