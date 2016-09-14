# coding:utf-8

from django.shortcuts import render
from django.http import HttpResponse
from web.models import ExGallery
from web.models import ExAuthor
from web.models import ExGalleryAuthorRelation
from web.models import ExGroup
from web.models import ExGalleryGroupRelation
from web.models import ExTag
from web.models import ExGalleryTagRelation
from web.models import tag_types
from django.db import transaction
import os
import pickle
import zipfile
import threading


# 一些常量的定义 =========================================================================================================
IMPORT_DICT = r'e:\import'
DST_DICT = r'e:\comic'
MAX_INSERT = 100


def import_galleries(request):
    """
    导入画集，导入时需要放在指定的文件夹下

    :param request:  url请求
    :return: 是否成功
    """
    task = ImportTask()
    task.start()
    return HttpResponse(u'import success!')


@transaction.atomic
def _import_galleries(filenames):

    def get_gallery(file_path):
        """
        读取zip文件中的gallery.pkl文件，生成gallery字典以及ExGallery实体类

        :param file_path: zip文件地址
        :return: Gallery字典，ExGallery实体类
        """
        _dic = None
        if file_path.endswith('zip'):
            with zipfile.ZipFile(file_path, mode='r', compression=zipfile.ZIP_STORED) as zip_file:
                for zfile in zip_file.namelist():
                    if zfile == 'gallery.pkl':
                        _dic = pickle.loads(zip_file.read(zfile))
        return _dic

    dics = []
    for file in filenames:
        dic = get_gallery(file)
        if dic:
            dics.append((dic, file))


    # 先获取所有已经存在的实体类
    gallery_ids, author_names, group_names, male_names, female_names, misc_names = [], [], [], [], [], []

    for tup in dics:
        dic = tup[0]
        gallery_ids.append(dic['root_path'].split('/')[4])
        author_names += dic['artist']
        group_names += dic['group']
        male_names += dic['male_tag']
        female_names += dic['female_tag']
        misc_names += dic['misc_tag']

    exist_galls = ExGallery.objects.values_list('id').filter(id__in=gallery_ids)
    exist_galls = {int(result[0]) for result in exist_galls}

    exist_authors = ExAuthor.objects.values_list('name').filter(name__in=author_names)
    exist_authors = {str(result[0]) for result in exist_authors}

    exist_groups = ExGroup.objects.values_list('name').filter(name__in=group_names)
    exist_groups = {str(result[0]) for result in exist_groups}

    exist_male = ExTag.objects.values_list('name').filter(name__in=male_names, type=tag_types['male_tag'])
    exist_male = {str(result[0]) for result in exist_male}

    exist_female = ExTag.objects.values_list('name').filter(name__in=female_names, type=tag_types['female_tag'])
    exist_female = {str(result[0]) for result in exist_female}

    exist_misc = ExTag.objects.values_list('name').filter(name__in=misc_names, type=tag_types['misc_tag'])
    exist_misc = {str(result[0]) for result in exist_misc}

    # 待插入列表
    galleries, gall_inserted, authors, groups, tags = [], [], [], [], []
    for tup in dics:
        dic = tup[0]
        gallery = ExGallery.get_object(dic)
        if gallery and gallery.id not in exist_galls:
            galleries.append(gallery)
            gall_inserted.append(gallery.id)

            # 处理作者
            for name in dic['artist']:
                if name not in exist_authors:
                    exist_authors.add(name)
                    authors.append(ExAuthor.get_object(name))

            # 处理同人团体
            for name in dic['group']:
                if name not in exist_groups:
                    exist_groups.add(name)
                    groups.append(ExGroup.get_object(name))

            # 处理标签
            for name in dic['male_tag']:
                if name not in exist_male:
                    exist_male.add(name)
                    tags.append(ExTag.get_object(name, 'male_tag'))
            for name in dic['female_tag']:
                if name not in exist_female:
                    exist_female.add(name)
                    tags.append(ExTag.get_object(name, 'female_tag'))
            for name in dic['misc_tag']:
                if name not in exist_misc:
                    exist_misc.add(name)
                    tags.append(ExTag.get_object(name, 'misc_tag'))

    ExGallery.objects.bulk_create(galleries)
    ExAuthor.objects.bulk_create(authors)
    ExGroup.objects.bulk_create(groups)
    ExTag.objects.bulk_create(tags)

    galleries = ExGallery.objects.filter(id__in=gall_inserted)
    galleries = {gallery.id: gallery for gallery in galleries}

    authors = ExAuthor.objects.filter(name__in=author_names)
    authors = {author.name: author for author in authors}

    groups = ExGroup.objects.filter(name__in=group_names)
    groups = {group.name: group for group in groups}

    tag_names = set(male_names + female_names + misc_names)
    tags = ExTag.objects.filter(name__in=tag_names)
    tags = {tag.name + '-' + str(tag.type): tag for tag in tags}

    # 处理关联关系
    aus, ags, ats = [], [], []
    for tup in dics:
        dic = tup[0]
        gid = int(dic['root_path'].split('/')[4])
        if gid in galleries:
            for name in dic['artist']:
                aus.append(ExGalleryAuthorRelation.get_object(gid, authors[name].id))
            for name in dic['group']:
                ags.append(ExGalleryGroupRelation.get_object(gid, groups[name].id))
            for name in dic['male_tag']:
                ats.append(ExGalleryTagRelation.get_object(gid, tags[name + '-' + str(tag_types['male_tag'])].id))
            for name in dic['female_tag']:
                ats.append(ExGalleryTagRelation.get_object(gid, tags[name + '-' + str(tag_types['female_tag'])].id))
            for name in dic['misc_tag']:
                ats.append(ExGalleryTagRelation.get_object(gid, tags[name + '-' + str(tag_types['misc_tag'])].id))

    # 最后做关联关系的插入
    ExGalleryAuthorRelation.objects.bulk_create(aus)
    ExGalleryGroupRelation.objects.bulk_create(ags)
    ExGalleryTagRelation.objects.bulk_create(ats)

    # 修改文件地址
    for tup in dics:
        dic = tup[0]
        gid = int(dic['root_path'].split('/')[4])
        if gid in galleries:
            gall = galleries[gid]
            new = os.path.join(DST_DICT, gall.save_path)
            if os.path.exists(tup[1]):
                os.renames(tup[1], new)


class ImportTask(threading.Thread):

    def run(self):
        imports = []
        for root, dirs, files in os.walk(IMPORT_DICT):
            for file in files:
                imports.append(os.path.join(root, file))
                if len(imports) >= MAX_INSERT:
                    _import_galleries(imports)
                    imports = []
        if len(imports) > 0:
            _import_galleries(imports)




