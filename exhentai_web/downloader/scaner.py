# coding=utf-8

import os
import pickle
import zipfile
import shutil
from exhentai_web.downloader.comicdownloader import ImageInfo

__author__ = 'mading01'


# 记录的方法 ============================================================================================================
LOG_LEVELS = ['info ', 'warn ', 'error', 'fatal']  # log级别

NOW_LEVEL = 0  # 当前的log级别


def log(info_mode, *args):
    """
    按格式输出信息。

    :param info_mode: 输出头部，格式为[info_mode]:
    :param args: 输出的内容
    :return: None
    """
    if info_mode >= NOW_LEVEL:
        print('[' + LOG_LEVELS[info_mode] + ']:', end=' ')
        for arg in args:
            print(arg, end=' ')
        print('')


# 实际实用的方法 =========================================================================================================
def local_check(path):
    """
    完全依据已经存储的image_info对下载状况进行检查，如果失败会写一个undone文件

    :param path: 文件夹地址
    :return: 是否成功
    """
    dic = os.path.join(path, 'gallery.pkl')
    log(0, 'check start ========================================')
    log(0, 'path:', path)
    if not os.path.exists(dic):
        log(1, 'path:', path, 'gallery.pkl doesn\'t exist.')
        log(1, 'check wrong.')
        return False

    undone = os.path.join(path, 'undone')
    right = True
    with open(dic, 'rb') as file:
        gallery = pickle.load(file)
    for info in gallery['imgs']:
        image = ImageInfo.from_dict(gallery['imgs'][info])
        if not image.check_all(path):
            with open(undone, 'w', encoding='utf-8') as file:
                log(2, 'check wrong! path:', path, 'page:', info)
                file.write('undone')
                right = False
        gallery['imgs'][info] = image.to_dict()

    # 检查正确，如果有undone，则移除之
    if right and os.path.exists(undone):
        os.remove(undone)

    # 删除不正确的文件
    for file in os.listdir(path):
        if not file in gallery['imgs']:
            os.remove(os.path.join(path, file))
    with open(dic, 'wb') as file:
        pickle.dump(gallery, file)
    log(0, 'check done.')
    return right


def renames(root, now, dst):
    """
    将文件夹转移到正确的存储地址

    :param root: 需要搜寻的文件夹
    :param now: 当前一层的文件夹名称
    :param dst: 目标根目录
    :return: None
    """
    if not os.path.isdir(root):
        return

    dic = os.path.join(root, 'gallery.pkl')
    if os.path.exists(dic):
        if not local_check(root):  # 检查出错，直接return
            return
        with open(dic, 'rb') as file:
            gallery = pickle.load(file)
        code = int(gallery['root_path'].split('/')[4])
        new = os.path.join(dst, '{:0>3}'.format(code % 100), now)
        log(0, 'renames:', new)
        os.renames(root, new)
    else:
        for path in os.listdir(root):
            renames(os.path.join(root, path), path, dst)


def _zip(path):
    """
    将一个文件进行压缩

    :param path: 文件路径
    :return: None
    """
    log(0, 'zip start:', path)
    file_name = path + '.zip'
    with zipfile.ZipFile(file_name, mode='w', compression=zipfile.ZIP_STORED) as zip_file:
        for file in os.listdir(path):
            fp = os.path.join(path, file)
            zip_file.write(fp, fp.replace(path + os.sep, ''))
    shutil.rmtree(path)


def zip_all(path):
    """
    对文件进行压缩，递归调用

    :param path: 需要压缩的根目录
    :return: None
    """
    if not os.path.isdir(path):
        return
    dic_path = os.path.join(path, 'gallery.pkl')
    if os.path.exists(dic_path):
        _zip(path)
    else:
        for d in os.listdir(path):
            zip_all(os.path.join(path, d))


def scan(root, dst):
    """
    批处理

    :param root: 处理根路径
    :param dst:  处理的目标路径
    :return: None
    """
    renames(root, '', dst)
    zip_all(dst)


if __name__ == '__main__':
    scan(r'e:\right', r'e:\comic')
