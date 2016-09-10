# coding:utf-8

from django.shortcuts import render
from django.http import HttpResponse
import exhentai_web.web.models as models
import os
import pickle
import zipfile


# 一些常量的定义 =========================================================================================================
IMPORT_DICT = r'e:\comic'
MAX_INSERT = 100


def import_galleries(request):
    """
    导入画集，导入时需要放在指定的文件夹下

    :param request:  url请求
    :return: 是否成功
    """
    inserts = []
    for root, dirs, files in os.walk(IMPORT_DICT):
        for file in files:
            gallery = get_gallery(os.path.join(root, file))
            if gallery:
                inserts.append(gallery)
            if len(inserts) >= MAX_INSERT:
                models.ExGallery.objects.bulk_create(inserts)
                inserts = []
    if len(inserts) > 0:
        models.ExGallery.objects.bulk_create(inserts)
    return HttpResponse(u'import success!')


def get_gallery(file_path):
    """
    读取zip文件中的gallery.pkl文件，生成ExGallery实体类

    :param zip_path: zip文件地址
    :return: ExGallery实体类
    """
    gall = None
    if file_path.endswith('zip'):
        with zipfile.ZipFile(file_path, mode='r', compression=zipfile.ZIP_STORED) as zip_file:
            for zfile in zip_file.namelist():
                if zfile == 'gallery.pkl':
                    dic = pickle.loads(zip_file.read(zfile))
                    gall = models.ExGallery.get_object(dic)
    return gall
