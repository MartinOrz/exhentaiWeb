# coding:utf-8

from django.shortcuts import render
from django.http import HttpResponse
from django.http import HttpResponseNotAllowed
from django.http import JsonResponse
from web.models import ExGallery
from web.models import ExAuthor
from web.models import ExGalleryAuthorRelation
from web.models import ExGroup
from web.models import ExGalleryGroupRelation
from web.models import ExTag
from web.models import ExGalleryTagRelation
from web.models import ExGalleryCPTagRelation
from web.models import tag_types
from web.models import status
from web.models import display_languages
from web.models import display_types
from django.db import transaction
from datetime import datetime
from exhentai_web import settings
import os
import pickle
import zipfile
import threading
import socket


# 一些常量的定义 =========================================================================================================
IMPORT_DICT = r'g:\import'
DST_DICT = r'g:\comic'
MAX_INSERT = 100
STATICFILES_DIRS = settings.STATICFILES_DIRS[0]
IP = socket.gethostbyname(socket.gethostname())


# 一些基本方法的定义 ======================================================================================================
def _get_success_json(data):
    """
    获取一个正确的Json格式相应

    :param data: 信息
    :return: JsonResponse
    """
    data = {'success': True, 'data': data}
    return JsonResponse(data=data)


def _get_error_json(data):
    """
    获取一个错误的Json格式相应

    :param data: 信息
    :return: JsonResponse
    """
    data = {'success': False, 'data': data}
    return JsonResponse(data=data)


def method_dispatch(**table):
    """
    根据http谓词进行方法路由

    :param table: 谓词-方法表
    :return: 相应结果
    """
    def invalid_method(request, *args, **kwargs):
        return HttpResponseNotAllowed(table.keys())

    def d(request, *args, **kwargs):
        handler = table.get(request.method, invalid_method)
        return handler(request, *args, **kwargs)
    return d


# 画集显示相关请求 =======================================================================================================
def get_gallery_info(request, gall):
    """
    获取画集信息，包含作者，tag信息等
    :param request:
    :param gall:
    :return:
    """
    try:
        now = request.GET['now'] if 'now' in request.GET else None
        gid = int(gall)
        # 先获取画集信息
        gallery = ExGallery.objects.get(id=gid)

        result = dict()
        result['title'] = gallery.name  # 页面标题
        result['id'] = gallery.id  # 画集id，作为全局变量存储
        result['type'] = display_types[gallery.type]
        result['length'] = gallery.length  # 画集长度，作为全局变量存储
        result['name_n'] = gallery.name_n  # 名称
        result['name_j'] = gallery.name_j  # 日文名称
        result['language'] = display_languages[gallery.language]
        result['translator'] = gallery.translator
        result['rating'] = gallery.rating
        result['posted'] = gallery.posted.strftime("%Y-%m-%d")

        result['first_page'] = int(now) if now else 1
        result['host'] = IP

        # Group信息
        g_relations = ExGalleryGroupRelation.objects.filter(gallery_id=gid)
        group_ids = [relation.group_id for relation in g_relations]
        groups = ExGroup.objects.filter(id__in=group_ids)
        result['groups'] = groups

        # Author信息
        a_relations = ExGalleryAuthorRelation.objects.filter(gallery_id=gid)
        author_ids = [relation.author_id for relation in a_relations]
        authors = ExAuthor.objects.filter(id__in=author_ids)
        result['authors'] = authors

        # Tag信息
        t_relations = ExGalleryTagRelation.objects.filter(gallery_id=gid)
        tag_ids = [relation.tag_id for relation in t_relations]
        tags = ExTag.objects.filter(id__in=tag_ids)
        result['male_tags'] = []
        result['female_tags'] = []
        result['misc_tags'] = []
        for tag in tags:
            if tag.type == tag_types['male_tag']:
                result['male_tags'].append(tag)
            elif tag.type == tag_types['female_tag']:
                result['female_tags'].append(tag)
            else:
                result['misc_tags'].append(tag)

        # 角色 同人信息
        cpt_relations = ExGalleryCPTagRelation.objects.filter(gallery_id=gid)
        cpt_ids = [relation.tag_id for relation in cpt_relations]
        cpts = ExTag.objects.filter(id__in=cpt_ids)
        result['characters'] = []
        result['parodies'] = []
        for cpt in cpts:
            if cpt.type == tag_types['character']:
                result['characters'].append(cpt)
            else:
                result['parodies'].append(cpt)
        return render(request, 'gallery.html', result)
    except Exception as e:
        print(e)
        return _get_error_json(None)


def get_gallery_id(request):
    """
    获取一个画集的id

    :param request: 请求
    :get_param status: 画集状态
    :get_param random: 是否随机选取，0为否，否则为是
    :return: 选取到的画集id
    """
    def set_add(set1, set2):
        if set1 is None:
            return set2
        return set1 & set2
    try:
        status = int(request.GET['status']) if 'status' in request.GET and request.GET['status'] != 'null' else 1
        rand = bool(request.GET['random']) if 'random' in request.GET else False

        gids = None

        # 处理团体
        group = request.GET['group']
        if group:
            groups = ExGroup.objects.filter(name__in=group.split('|'))
            groupids = [group.id for group in groups]
            gids = set_add(gids, {g.gallery_id for g in ExGalleryGroupRelation.objects.filter(group_id__in=groupids)})

        # 处理作者
        author = request.GET['author']
        if author:
            authors = ExAuthor.objects.filter(name__in=author.split('|'))
            authorids = [author.id for author in authors]
            gids = set_add(gids, {a.gallery_id for a in ExGalleryAuthorRelation.objects.filter(author_id__in=authorids)})

        # 处理标签
        tag = request.GET['tag']
        if tag:
            tags = ExTag.objects.filter(name__in=tag.split('|'))
            tagids = [tag.id for tag in tags]
            gids = set_add(gids, {t.gallery_id for t in ExGalleryTagRelation.objects.filter(tag_id__in=tagids)})

        # 处理角色以及cp
        c = request.GET['character']
        p = request.GET['parody']
        cps = []
        if c:
            cps += c.split('|')
        if p:
            cps += p.split('|')
        if cps:
            tags = ExTag.objects.filter(name__in=cps)
            tagids = [tag.id for tag in tags]
            gids = set_add(gids, {t.gallery_id for t in ExGalleryCPTagRelation.objects.filter(tag_id__in=tagids)})

        if gids is None:  # 这种情况没有任何参数
            galls = ExGallery.objects.filter(status=status)
        elif len(gids) > 0:  # 这种情况查询到了相应结果
            galls = ExGallery.objects.filter(id__in=gids, status=status)
        else:  # 这种情况没有对应结果
            return _get_success_json(-1)
        result = (galls.order_by('?')[0].id if rand else galls[0].id) if len(galls) > 0 else -1
        return _get_success_json(result)
    except Exception as e:
        print(e)
        return _get_error_json(None)


@transaction.atomic
def update_gallery(request, gall):
    """
    修改画集属性，只有 status, translator, rating, last_view. 由于django不能支持http put,因此使用post

    :param request: 请求
    :param gall: 画集id
    :return: 是否成功
    """
    try:
        gid = int(gall)
        gallery = ExGallery.objects.get(id=gid)
        if 'status' in request.POST:
            gallery.status = status.get(request.POST, gallery.status)
        if 'translator' in request.POST and request.POST['translator'].strip():
            gallery.translator = request.POST['translator']
        if 'rating' in request.POST:
            gallery.rating = min(100, max(0, int(request.POST['rating'])))
        gallery.last_view = datetime.now()
        gallery.save()
        return _get_success_json(None)
    except Exception as e:
        return _get_error_json(None)


@transaction.atomic
def delete_gallery(request, gall):
    """
    删除一个画集，删除时会更新画集的信息，同时从物理上彻底删除画集zip文件

    :param gall: 画集id
    :return: 是否成功
    """
    try:
        gid = int(gall)
        # 先获取画集信息
        gallery = ExGallery.objects.get(id=gid)
        gallery.status = status['deleted']
        gallery.save()
        file = os.path.join(DST_DICT, gallery.save_path)
        if os.path.exists(file):
            os.remove(file)
        return _get_success_json(None)
    except Exception as e:
        return _get_error_json(None)


def get_gallery_img(request, gall, img):
    """
    获取一张图片, REST路径为 '/画集id/图片页码'

    :param request: http请求
    :param gall: 画集id
    :param img: 图片页码
    :return: 正确则返回图像，否则返回错误图像
    """
    try:
        gallery = ExGallery.objects.get(id=int(gall))
        file = os.path.join(DST_DICT, gallery.save_path)
        img = "{:0>3}".format(img)
        with zipfile.ZipFile(file, mode='r', compression=zipfile.ZIP_STORED) as zip_file:
            for zfile in zip_file.namelist():
                if zfile.startswith(img):
                    return HttpResponse(zip_file.read(zfile), content_type='image/' + zfile.split('.')[-1])
    except Exception as e:
        pass
    with open(os.path.join(STATICFILES_DIRS, 'resources', 'err_img.png'), 'rb') as file:
        return HttpResponse(file.read(), content_type='image/png')


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
    gallery_ids, author_names, group_names, male_names, female_names, misc_names, character_names, parody_names \
        = [], [], [], [], [], [], [], []

    for tup in dics:
        dic = tup[0]
        gallery_ids.append(dic['root_path'].split('/')[4])
        author_names += dic['artist']
        group_names += dic['group']
        male_names += dic['male_tag']
        female_names += dic['female_tag']
        misc_names += dic['misc_tag']
        character_names += dic['character']
        parody_names += dic['parody']

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

    exist_character = ExTag.objects.values_list('name').filter(name__in=character_names, type=tag_types['character'])
    exist_character = {str(result[0]) for result in exist_character}

    exist_parody = ExTag.objects.values_list('name').filter(name__in=parody_names, type=tag_types['parody'])
    exist_parody = {str(result[0]) for result in exist_parody}

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
            for name in dic['character']:
                if name not in exist_character:
                    exist_character.add(name)
                    tags.append(ExTag.get_object(name, 'character'))
            for name in dic['parody']:
                if name not in exist_parody:
                    exist_parody.add(name)
                    tags.append(ExTag.get_object(name, 'parody'))

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

    tag_names = set(male_names + female_names + misc_names + character_names + parody_names)
    tags = ExTag.objects.filter(name__in=tag_names)
    tags = {tag.name + '-' + str(tag.type): tag for tag in tags}

    # 处理关联关系
    aus, ags, ats, acs = [], [], [], []
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
            for name in dic['character']:
                acs.append(ExGalleryCPTagRelation.get_object(gid, tags[name + '-' + str(tag_types['character'])].id))
            for name in dic['parody']:
                acs.append(ExGalleryCPTagRelation.get_object(gid, tags[name + '-' + str(tag_types['parody'])].id))

    # 最后做关联关系的插入
    ExGalleryAuthorRelation.objects.bulk_create(aus)
    ExGalleryGroupRelation.objects.bulk_create(ags)
    ExGalleryTagRelation.objects.bulk_create(ats)
    ExGalleryCPTagRelation.objects.bulk_create(acs)

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


# 标签相关请求 ===========================================================================================================
def get_tag(request, t):
    try:
        tid = int(t)
        tag = ExTag.objects.get(id=tid)
        return render(request, 'tagEdit.html', tag.to_dict())
    except Exception as e:
        return _get_error_json(None)

@transaction.atomic
def update_tag(request, t):
    """
    更新一个标签

    :param request: 请求
    :param t: 标签id
    :return: 是否成功
    """
    try:
        tid = int(t)
        tag = ExTag.objects.get(id=tid)
        if 'text' in request.POST and request.POST['text'].strip():
            tag.text = request.POST['text'].strip()
        if 'info' in request.POST and request.POST['info'].strip():
            tag.info = request.POST['info']
        tag.save()
        return _get_success_json(None)
    except Exception as e:
        return _get_error_json(None)

