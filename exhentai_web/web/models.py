# coding=utf-8
from django.db import models
import os


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

# 标签类型
tag_types = {
    'male_tag': 0,
    'female_tag': 1,
    'misc_tag': 2,
}


class ExGallery(models.Model):
    """
    用于存储的画集实体类
    """
    id = models.IntegerField(primary_key=True)
    root_path = models.CharField(max_length=100)
    save_path = models.CharField(max_length=500)
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
        code = int(root_path.split('/')[4])
        result.id = code
        result.root_path = root_path
        result.save_path = os.path.join('{:0>3}'.format(code % 100), dic['name'])
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
        result.rating = DEFAULT_RATING
        result.status = status[DEFAULT_STATUS]
        result.last_view = '2016-01-01 00:00:00'
        return result


class ExAuthor(models.Model):
    """
    用于存储作者的实体类
    """
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    text = models.CharField(max_length=255)
    refer = models.IntegerField()
    rating = models.IntegerField()

    @staticmethod
    def get_object(name):
        """
        根据给定的名称生成一个ExAuthor

        :param name: 作者名称
        :return: 生成的ExAuthor实体类
        """
        result = ExAuthor()
        result.name = name
        result.text = ''
        result.refer = 0
        result.rating = DEFAULT_RATING
        return result


class ExGalleryAuthorRelation(models.Model):
    """
    画集与作者的关系类
    """
    id = models.IntegerField(primary_key=True)
    gallery_id = models.IntegerField(db_index=True)
    author_id = models.IntegerField(db_index=True)

    @staticmethod
    def get_object(gallery_id, author_id):
        """
        根据给定的名称生成一个ExGalleryAuthorRelation

        :param gallery_id: 画集id
        :param author_id: 作者id
        :return: 生成的ExGalleryAuthorRelation实体类
        """
        result = ExGalleryAuthorRelation()
        result.gallery_id = gallery_id
        result.author_id = author_id
        return result


class ExGroup(models.Model):
    """
    用于存储同人团体的实体类
    """
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    text = models.CharField(max_length=255)
    rating = models.IntegerField()

    @staticmethod
    def get_object(name):
        """
        根据给定的名称生成一个ExGroup

        :param name: 作者名称
        :return: 生成的ExGroup实体类
        """
        result = ExGroup()
        result.name = name
        result.text = ''
        result.rating = DEFAULT_RATING
        return result


class ExGalleryGroupRelation(models.Model):
    """
    画集与同人团体的关系
    """
    id = models.IntegerField(primary_key=True)
    gallery_id = models.IntegerField(db_index=True)
    group_id = models.IntegerField(db_index=True)

    @staticmethod
    def get_object(gallery_id, group_id):
        """
        根据给定的名称生成一个ExGalleryGroupRelation

        :param gallery_id: 画集id
        :param group_id: group的id
        :return: 生成的ExGalleryGroupRelation实体类
        """
        result = ExGalleryGroupRelation()
        result.gallery_id = gallery_id
        result.group_id = group_id
        return result


class ExTag(models.Model):
    """
    用于存储标签的实体类
    """
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    text = models.CharField(max_length=255)
    type = models.IntegerField(db_index=True)

    @staticmethod
    def get_object(name, type_name):
        """
        根据给定的名称生成一个ExTag

        :param name: tag名称
        :param type_name: 作者id
        :return: 生成的ExTag实体类
        """
        result = ExTag()
        result.name = name
        result.text = ''
        result.type = tag_types[type_name]
        return result


def get_gallery_tag_relation(gallery_id, tag_id):
    """
    获取一个画集与标签关联关系的实体类，分4张表，根据画集id分表
    :param gallery_id:
    :param tag_id:
    :return:
    """
    mod = gallery_id % 4
    if mod == 0:
        return ExGalleryTagRelation0(gallery_id, tag_id)
    elif mod == 1:
        return ExGalleryTagRelation1(gallery_id, tag_id)
    elif mod == 2:
        return ExGalleryTagRelation2(gallery_id, tag_id)
    else:
        return ExGalleryTagRelation3(gallery_id, tag_id)


class ExGalleryTagRelation0(models.Model):
    """
    用于存储画集与标签关系的表0
    """
    id = models.IntegerField(primary_key=True)
    gallery_id = models.IntegerField(db_index=True)
    tag_id = models.IntegerField(db_index=True)

    @staticmethod
    def get_object(gallery_id, tag_id):
        """
        根据给定的名称生成一个ExGalleryTagRelation0

        :param gallery_id: 画集id
        :param tag_id: 标签id
        :return: 生成的ExGalleryTagRelation0实体类
        """
        result = ExGalleryTagRelation0()
        result.gallery_id = gallery_id
        result.tag_id = tag_id
        return result


class ExGalleryTagRelation1(models.Model):
    """
    用于存储画集与标签关系的表1
    """
    id = models.IntegerField(primary_key=True)
    gallery_id = models.IntegerField(db_index=True)
    tag_id = models.IntegerField(db_index=True)

    @staticmethod
    def get_object(gallery_id, tag_id):
        """
        根据给定的名称生成一个ExGalleryTagRelation1

        :param gallery_id: 画集id
        :param tag_id: 标签id
        :return: 生成的ExGalleryTagRelation1实体类
        """
        result = ExGalleryTagRelation1()
        result.gallery_id = gallery_id
        result.tag_id = tag_id
        return result


class ExGalleryTagRelation2(models.Model):
    """
    用于存储画集与标签关系的表2
    """
    id = models.IntegerField(primary_key=True)
    gallery_id = models.IntegerField(db_index=True)
    tag_id = models.IntegerField(db_index=True)

    @staticmethod
    def get_object(gallery_id, tag_id):
        """
        根据给定的名称生成一个ExGalleryTagRelation2

        :param gallery_id: 画集id
        :param tag_id: 标签id
        :return: 生成的ExGalleryTagRelation2实体类
        """
        result = ExGalleryTagRelation2()
        result.gallery_id = gallery_id
        result.tag_id = tag_id
        return result


class ExGalleryTagRelation3(models.Model):
    """
    用于存储画集与标签关系的表3
    """
    id = models.IntegerField(primary_key=True)
    gallery_id = models.IntegerField(db_index=True)
    tag_id = models.IntegerField(db_index=True)

    @staticmethod
    def get_object(gallery_id, tag_id):
        """
        根据给定的名称生成一个ExGalleryTagRelation3

        :param gallery_id: 画集id
        :param tag_id: 标签id
        :return: 生成的ExGalleryTagRelation3实体类
        """
        result = ExGalleryTagRelation3()
        result.gallery_id = gallery_id
        result.tag_id = tag_id
        return result
