# coding:utf-8

from django.shortcuts import render
from django.http import HttpResponse
import exhentai_web.web.models as models
from django.db import transaction
import os
import pickle
import zipfile
import threading


# 一些常量的定义 =========================================================================================================
IMPORT_DICT = r'e:\comic'
MAX_INSERT = 100


def import_galleries(request):
    """
    导入画集，导入时需要放在指定的文件夹下

    :param request:  url请求
    :return: 是否成功
    """

    return HttpResponse(u'import success!')


@transaction.commit_on_success
def import_galleries(dics):
    galleries = []  # 用以存储需要导入的画集
    author_names = []  # 用以存储本次导入需要添加的作者名称
    group_names = []  # 用以存储本次导入需要添加的同人团体名称
    tag_names = []  # 用以存储本次导入添加的标签名称

    # 先导入gallery，并且生成author_nbames, group_names, tag_names
    for dic in dics:
        gallery = models.ExGallery.get_object(dic)
        if gallery:
            galleries.append(gallery)
            author_names += dic['author']
            group_names += dic['group']
            tag_names += [(name, models.tag_types['male_tag']) for name in dic['male_tag']]
            tag_names += [(name, models.tag_types['female_tag']) for name in dic['female_tag']]
            tag_names += [(name, models.tag_types['misc_tag']) for name in dic['misc_tag']]
    models.ExGallery.objects.bulk_create(galleries)

    # 查询作者信息
    exist_authors = models.ExAuthor.objects.get()



class ImportTask(threading.Thread):

    def run(self):
        def get_gallery(file_path):
            """
            读取zip文件中的gallery.pkl文件，生成gallery字典以及ExGallery实体类

            :param file_path: zip文件地址
            :return: Gallery字典，ExGallery实体类
            """
            dic, gall = None
            if file_path.endswith('zip'):
                with zipfile.ZipFile(file_path, mode='r', compression=zipfile.ZIP_STORED) as zip_file:
                    for zfile in zip_file.namelist():
                        if zfile == 'gallery.pkl':
                            dic = pickle.loads(zip_file.read(zfile))
                            gall = models.ExGallery.get_object(dic)
            return dic, gall




