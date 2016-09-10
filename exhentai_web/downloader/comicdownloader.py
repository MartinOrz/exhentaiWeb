# coding=utf-8

import codecs
import glob
import queue
import os
import pickle
import re
import threading
import time
import urllib.error
import requests
import PIL.Image as Image

__author__ = 'mading01'

# 用到的页面地址 =========================================================================================================
''' 登陆页面 '''
loginPage = 'https://forums.e-hentai.org/index.php?act=Login&CODE=01'

''' 里站主页 '''
exhentaiRoot = 'http://exhentai.org/'

''' 超限时gif的地址 '''
wrongGif = 'https://exhentai.org/img/509.gif'

# 全局变量，登录信息，只保存一次 ============================================================================================
MEMBER_ID, PASS_HASH = None, None

# 全局变量 是否发生了403 ==================================================================================================
HAS_403 = False


# 登录相关工作 ===========================================================================================================
def connect_to_exhentai(username, password):
    """ 连接到exhentai。
        登录里站时，需要先登录表站，然后使用表站的cookie访问里站的页面，即可正常访问里站。此方法在任何下载任务前必须先执行

        returns:
            - member_id: 用于生成header
            - pass_hash: 用于生成header
    """
    global MEMBER_ID, PASS_HASH, loginPage
    headers = {'User-agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)'}
    data = {'returntype': 8, 'CookieDate': 1, 'b': 'd', 'bt': 'pone', 'UserName': username, 'PassWord': password}
    response = requests.post(loginPage, data=data, headers=headers)
    cookies = response.cookies.get_dict()
    MEMBER_ID = cookies['ipb_member_id']
    PASS_HASH = cookies['ipb_pass_hash']


def gen_headers(referer=''):
    """
    生成一个随机的请求头部

    :param referer: 请求头部的referer信息
    :return: 生成的请求头
    """
    global MEMBER_ID, PASS_HASH
    if not MEMBER_ID:  # 未登录
        Exception('Please login first!')
    user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.81 ' + \
                 'Safari/537.36'
    h_cookie = 'nw=1;ipb_member_id=' + MEMBER_ID + ';ipb_pass_hash=' + PASS_HASH + ';'
    headers = {'User-Agent': user_agent, 'Accept-Language': 'zh-CN,zh;q=0.8', 'Accept-Charset': 'utf-8;q=0.7,*;q=0.7',
               'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Connection': 'keep-alive',
               'Cookie': h_cookie}
    return headers


# 基本信息1: 页面地址, 英文名称, 日文(中文)名称 ==============================================================================
gallery = re.compile('http[s]*://exhentai.org/g/\d+/[^/]+/')
name_n = re.compile('<h1 id="gn">([^<]*)</h1>')
name_j = re.compile('<h1 id="gj">([^<]*)</h1>')

# 基本信息2: 类型, 语言, 汉化组 ============================================================================================
comic_type = re.compile('<div id="gdc"><a href="http[s]*://exhentai\.org/([a-z-]+)">')
language = re.compile('<tr><td class="gdt1">Language:</td><td class="gdt2">([\S]+).+?</td></tr>')
translator = re.compile('[『|\(|\[|【]([^『^\(^\[^【]+[汉|漢]化[^』^\]^\)^】]*)[』|\]|\)|】]')

# 基本信息3: 页码长度, 长度, 发布时间 =======================================================================================
page = re.compile('<td onclick="document.location=this.firstChild.href"><a \S+ onclick="return false">(\d+)</a></td>')
length = re.compile('<tr><td class="gdt1">Length:</td><td class="gdt2">(\d+) pages</td></tr>')
posted = re.compile('<td class="gdt1">Posted:</td><td class="gdt2">(\d{4}-\d{2}-\d{2} \d{2}:\d{2})</td>')

# 基本信息4: 是否是杂志, 同人作品, 同人角色 ==================================================================================
anthology = re.compile('td_anthology')
parody = re.compile('<div id="td_parody:([^"]+)"')
character = re.compile('id="td_character:(\S+?)"')

# 作者信息: group, artist ===============================================================================================
group = re.compile('<div id="td_group:([^"]+)"')
artist = re.compile('<div id="td_artist:([^"]+)"')

# tag信息: male, female, mis ===========================================================================================
male_tag = re.compile('<div id="td_male:([^"]+)"')
female_tag = re.compile('<div id="td_female:([^"]+)"')
misc_tag = re.compile('<td class="tc">misc:</td><td>(<div .+?</div>)+</td>')
misc_detail = re.compile('<div id="td_(\S+?)" .+?</div>')

# 下载信息: 页码信息, 每页信息, 具体图片地址信息, 图片大小信息, 原图信息, 其他图片页面信息 ==========================================
pic = re.compile('<a href="(http[s]*://exhentai\.org/s/[^/]+/\d+-\d+)"><img')
img = re.compile('<div id="i3"><a onclick="[^"]+" href="[^"]+">\s*<img id="img" src="([^"]+)"')
img_info = re.compile('<div id="i4"><div>[^:]+:: (\d+) x (\d+).*?</div>')
original_source = re.compile('<a href="([^"]+)">Download original (\d+) x (\d+).*?source</a>')
another_source = re.compile('<a href="#".*?onclick="return nl\(([^\)]+)\)">Click here if the image fails loading</a>')


# 基本信息1: 页面地址, 英文名称, 日文(中文)名称 ==============================================================================
def find_name_n(input_content):
    """
    从gallery中获取n类型的名称。n类型名称为英文名

    :param input_content: 需要解析的页面内容
    :return: 解析结果
    """
    return name_n.findall(input_content)[0]


def find_name_j(input_content):
    """
    从gallery中获取j类型的名称。j类型名称为日文名

    :param input_content: 需要解析的页面内容
    :return: 解析结果
    """
    return name_j.findall(input_content)[0]


# 基本信息2: 类型, 语言, 汉化组 ============================================================================================
def find_type(input_content):
    """
    从gallery中获取类型信息
    :param input_content: 需要解析的页面内容
    :return: 类型信息
    """
    return comic_type.findall(input_content)[0]


def find_language(input_content):
    """
    从gallery中获取语言。对于原生日语内容，则返回'default'。
    :param input_content: 需要解析的页面内容
    :return: 解析结果
    """
    tmp = language.findall(input_content)
    if tmp:
        return tmp[0]
    else:
        return 'default'


def find_translator(input_content):
    """
    获取汉化组。没有则返回None
    :param input_content: 需要解析的页面内容
    :return: 解析结果
    """
    tmp = translator.findall(input_content)
    if tmp:
        return tmp[0]
    else:
        return None


# 基本信息3: 页码长度, 长度, 发布时间 =======================================================================================
def find_pages(input_content):
    """
    获取所有的页码页。
    页码指的是<td onclick="sp(1)">这样的一段内容，其指出了一共有多少页码。

    :param input_content: 需要解析的页面内容
    :return: 最大的页码值
    """
    pages = [int(x) for x in page.findall(input_content)]
    if not pages:
        return 1
    return max(pages)


def find_length(input_content):
    """
    从gallery中获取长度信息，即有多少页

    :param input_content: 需要解析的页面内容
    :return: 作品长度
    """
    return length.findall(input_content)[0]


def find_posted(input_content):
    """
    从gallery中获取发表时间
    :param input_content: 需要解析的页面内容
    :return: 解析结果
    """
    return posted.findall(input_content)[0]


# 基本信息4: 是否是杂志, 同人作品, 同人角色 ==================================================================================
def find_anthology(input_content):
    """
    判断是否是杂志。
    :param input_content: 需要解析的页面内容
    :return: True 如果是杂志，否则为False
    """
    return len(anthology.findall(input_content)) > 0


def find_parody(input_content):
    """
    从gallery中获取同人的作品。如果是原创作品则返回'original'。
    :param input_content: 需要解析的页面内容
    :return: 解析结果
    """
    tmp = parody.findall(input_content)
    if tmp:
        return tmp
    else:
        return ['original']


def find_characters(input_content):
    """
    从gallery中获取charater信息。charater即是指此同人的角色信息
    :param input_content: 需要解析的页面内容
    :return: 解析结果
    """
    return character.findall(input_content)


# 作者信息: group, artist ===============================================================================================
def find_group(input_content):
    """
    从gallery中获取group信息。group即是指作者所在的同人社团。没有则返回'none'
    :param input_content: 需要解析的页面内容
    :return: 解析结果
    """
    return group.findall(input_content)


def find_artists(input_content):
    """
    从gallery中获取所有的作者信息。作者可能有多个，因此返回的是列表形式。没有则返回空列表。
    :param input_content: 需要解析的页面内容
    :return: 解析结果
    """
    return artist.findall(input_content)


# tag信息: male, female, mis ===========================================================================================
def find_male_tag(input_content):
    """
    从gallery中获取所有的男性标签。返回为列表形式。没有则为空列表。
    :param input_content: 需要解析的页面内容
    :return: 解析结果
    """
    return male_tag.findall(input_content)


def find_female_tag(input_content):
    """
    从gallery中获取所有的女性标签。返回为列表形式。没有则为空列表。
    :param input_content: 需要解析的页面内容
    :return: 解析结果
    """
    return female_tag.findall(input_content)


def find_misc_tag(input_content):
    """
    从gallery中获取所有的杂项标签。返回为列表形式，没有则为空列表
    :param input_content: 需要解析的页面内容
    :return: 解析结果
    """
    miscs = misc_tag.findall(input_content)
    if miscs:
        return [misc_detail.findall(misc)[0] for misc in miscs]
    else:
        return []


# 下载信息: 页码信息, 每页信息, 具体图片地址信息, 图片大小信息, 原图信息, 其他图片页面信息 ==========================================
def find_pics(input_content):
    """
    从gallery中解析出所有的图片页面地址

    :param input_content: 需要解析的页面内容
    :return: 列表形式的图片页面地址
    """
    return pic.findall(input_content)


def find_img(input_content):
    """
    从某个图面页面中获取图片的具体地址

    :param input_content:  需要解析的页面内容
    :return: 解析出的图片地址
    """
    return img.findall(input_content)[0]


def find_img_info(input_content):
    """
    从某个图片页面中获取图片的信息。用以检查下载的图片是否正确

    :param input_content: 需要解析的页面内容
    :return: 图片信息信息
    """
    result = img_info.findall(input_content)[0]
    return int(result[0]), int(result[1])


def find_original_info(input_content):
    """
    尝试寻找原始图片信息（更清晰）
    :param input_content:  需要解析的页面内容
    :return: 原图图片信息
    """
    ori = original_source.findall(input_content)
    if not ori:
        return 0, 0
    result = ori[0]
    return int(result[1]), int(result[2])


def find_original_path(input_content):
    """
    尝试寻找原图图源
    :param input_content: 需要解析的页面内容
    :return: 原图地址，没有则为None
    """
    ori = original_source.findall(input_content)
    if ori:
        return ori[0][0].replace('&amp;', '&')
    return None


def find_another_img(input_content):
    """
    当图片下载失败的时候尝试换个图源

    :param input_content: 需要解析的页面内容
    :return: 新图源的页面后缀
    """
    return another_source.findall(input_content)[0][1:-1]


# 一些工具方法 ===========================================================================================================
def get_img_size(file):
    try:
        with Image.open(file) as _img:
            real_width, real_height = _img.size
        return real_width, real_height
    except Exception as e:
        log(2, file, 'check file failed.')
        return 0, 0


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


# 承载下载信息的类 =======================================================================================================
class Gallery:
    """
    一个画集，即具体下载的一部作品。
    """

    def __init__(self, rpath):
        """
        初始化函数。gallery以基本路径作为基础，包含了以下参数：

        - root_path: 路径，形式为 http://exhentai.org/g/837492/04c9db1aa5/
        - name_n: 英文名称
        - name_j: 日文名称
        - name: 作品名称，取日文名，如无日文名则取英文名

        - type: 作品类型
        - language: 作品语言
        - translator: 汉化组

        - pages: 页码，即此画集包含多少页页面
        - length: 作品长度，即共有多少图片
        - posted: 发布时间

        - is_anthology: 是否是杂志
        - parody: 同人作品
        - character: 同人角色

        - group: 同人社团
        - artist: 作者

        - male_tag: 男性标签
        - female_tag: 女性标签
        - misc_tag: 杂项标签

        - img_info: 所有图片的信息列表
        - save_path: 实际的保存地址

        :param rpath: gallery的基本路径
        :return: 类型实例
        """
        self.root_path = rpath
        self.name_n = ''
        self.name_j = ''
        self.name = ''

        self.type = ''
        self.language = ''
        self.translator = ''

        self.pages = 0
        self.length = 0
        self.posted = ''

        self.is_anthology = False
        self.parody = []
        self.character = []

        self.group = []
        self.artist = []

        self.male_tag = []
        self.female_tag = []
        self.misc_tag = []

        self.imgs = dict()
        self.save_path = ''

    def analysis_pages(self, save_path):
        """
        根据gallery路径分析页面内容，填充数据。

        :param save_path: 图片存储地址
        :return: 读取的页面内容，可供进一步解析
        """
        log(0, '开始分析作品内容 ================================================================')
        _content = requests.get(self.root_path, headers=gen_headers(), timeout=60).text

        # 获取语言和名称，汉化组。中文由于需要寻找汉化组，所以处理方式不一样
        self.language = find_language(_content)
        if self.language == 'Chinese':
            name1 = find_name_n(_content)
            name2 = find_name_j(_content)
            self.name_n = name1
            self.name_j = name2
            trans1 = find_translator(name1)
            trans2 = None
            if name2:
                trans2 = find_translator(name2)
                self.name = name2
            else:
                self.name = name1

            if trans2:
                self.translator = trans2
            elif trans1:
                self.translator = trans1
            else:
                self.translator = '未知汉化'
        else:
            # 解析名称，如果有日文名则设置为日文名，否则设置为英文名
            self.name_j = find_name_j(_content)
            self.name_n = find_name_n(_content)
            if self.name_j:
                self.name = self.name_j
            else:
                self.name = self.name_n
            self.translator = 'none'

        invalid_chars = '?*"<>/;:|'
        for char in invalid_chars:
            self.name = self.name.replace(char, ' ')
        log(0, '获取作品名称结束:', codecs.encode(self.name, 'gbk', 'ignore').decode('gbk'))
        self.type = find_type(_content)

        # 解析长度
        self.pages = int(find_pages(_content))
        self.length = int(find_length(_content))
        log(0, '获取作品长度结束，共:', self.pages, '页面, ', self.length, '页')
        self.posted = find_posted(_content)

        self.is_anthology = find_anthology(_content)
        self.parody = find_parody(_content)
        self.character = find_characters(_content)

        self.group = find_group(_content)
        self.artist = find_artists(_content)

        self.male_tag = find_male_tag(_content)
        self.female_tag = find_female_tag(_content)
        self.misc_tag = find_misc_tag(_content)

        # 获取所有图片地址
        # 第一页单独获取，因为content已经拿到，同时不需要添加p=?的参数
        tasks = []
        self.save_path = os.path.join(save_path, self.name)
        for p in find_pics(_content):
            task = ImageDownloadTask(self.root_path, p, self.save_path)
            tasks.append(task)
        log(0, '从第1页获取图片列表结束, 当前的图片列表长度:', len(tasks))

        ref = self.root_path
        for i in range(1, self.pages):
            now_page = self.root_path + '?p=' + str(i)
            tmp = requests.get(now_page, headers=gen_headers(ref), timeout=60).text
            for p in find_pics(tmp):
                task = ImageDownloadTask(self.root_path, p, self.save_path)
                tasks.append(task)
            log(0, '从第' + str(i + 1) + '页获取图片列表结束, 当前的图片列表长度:', len(tasks))
            ref = now_page
        return tasks

    def to_dict(self):
        """
        变形为一个dict以存储
        """
        dic = dict()
        dic['root_path'] = self.root_path
        dic['name_n'] = self.name_n
        dic['name_j'] = self.name_j
        dic['name'] = self.name

        dic['type'] = self.type
        dic['language'] = self.language
        dic['translator'] = self.translator

        dic['pages'] = self.pages
        dic['length'] = self.length
        dic['posted'] = self.posted

        dic['is_anthology'] = self.is_anthology
        dic['parody'] = self.parody
        dic['character'] = self.character

        dic['group'] = self.group
        dic['artist'] = self.artist

        dic['male_tag'] = self.male_tag
        dic['female_tag'] = self.female_tag
        dic['misc_tag'] = self.misc_tag
        dic['imgs'] = self.imgs

        return dic

    def mkdir(self):
        """
        下载时创建文件夹

        :return: None
        """
        if not os.path.exists(self.save_path):  # 下载前先创建文件夹
            os.mkdir(self.save_path)

    def save_dict(self):
        """
        使用pickle储存所有内容

        :return: None
        """
        with open(os.path.join(self.save_path, 'gallery.pkl'), 'wb') as file:
            pickle.dump(self.to_dict(), file)


# 一张图片的下载信息以及图片信息类 ===========================================================================================
class ImageDownloadTask:
    """
    一个图片下载的任务，仅仅承载一张图片的下载。
    """

    def __init__(self, root_path, url, save_path):
        """
        初始化函数，此类主要包括参数如下：

        - root_path: gallery主页地址
        - url: 待下载页面地址
        - save_path: 文件的保存地址
        - page: 当前图片是第几页

        - ori: 原图下载地址，没有原图则为None

        - src: 图片下载地址
        - try_times: 已经尝试的次数

        - img_info: 图片信息

        :param root_path: gallery主页地址
        :param url: 当前页面地址
        :param save_path: 保存地址
        :return: 类型实例
        """
        self.root_path = root_path
        self.url = url
        self.save_path = save_path
        self.page = self.url.split('?')[0].split('-')[-1]

        self.try_times = 0  # 重试次数
        self.img_info = None
        self.src = None
        self.ori = None

    def gen_image_info(self):
        """
        分析当前下载页面的下载信息

        :return: None
        """
        info = ImageInfo(self.url, self.page)
        response = requests.get(self.url, headers=gen_headers(referer=self.root_path), timeout=60)
        _content = response.text
        info.width, info.height = find_img_info(_content)
        info.width_ori, info.height_ori = find_original_info(_content)

        # 图片下载地址
        self.img_info = info
        self.src = find_img(_content)
        self.ori = find_original_path(_content)

    def download(self):
        """
        进行一次下载，如果有原图则下载原图。否则下载普通图片。

        :return: 是否下载成功
        """
        self.try_times += 1
        if not self.img_info:
            try:
                self.gen_image_info()
            except Exception as e:
                log(2, 'gen image info wrong:', e)
                self.img_info = None
                self.find_another_src()
                return False

        file_name = self.download_ori() if self.ori else self.download_normal()
        if file_name:  # 下载成功
            self.img_info.download_name = os.path.basename(file_name)  # 设置下载名称
            return True
        return False

    def download_ori(self):
        """
        尝试下载原图，失败则尝试次数加1

        :return: 是否下载成功
        """
        global HAS_403

        downloaded = self.img_info.check_ori(self.save_path)
        if downloaded:
            return downloaded

        try:
            response = requests.get(self.ori, headers=gen_headers(self.url), timeout=120)
            _content = response.content
            suffix = response.url.split('?')[0].split('.')[-1]
            if suffix == 'php':  # 此时已发生403
                HAS_403 = True
                return None
            file_name = os.path.join(self.save_path, '{:0>3}_ori.{}'.format(self.page, suffix))
            with open(file_name, 'wb') as _file:
                _file.write(_content)
            return self.img_info.check_ori(self.save_path)
        except Exception as e:
            log(2, self.ori, "open url failed.", e)
            if isinstance(e, urllib.error.HTTPError) and str(e.code) == '403':
                HAS_403 = True
        return None

    def download_normal(self):
        """
        下载一张图片，非原图。失败则寻找新图源

        :return: 是否成功
        """
        global HAS_403, wrongGif

        downloaded = self.img_info.check_normal(self.save_path)
        if downloaded:
            return downloaded

        if self.src == wrongGif:  # 此时已发生403
            HAS_403 = True
            return None

        response = None
        try:
            response = requests.get(self.src, headers=gen_headers(self.url), timeout=120)
            _content = response.content
            suffix = self.src.split('.')[-1]
            file_name = os.path.join(self.save_path, '{:0>3}.{}'.format(self.page, suffix))
            with open(file_name, 'wb') as _file:
                _file.write(_content)
            return self.img_info.check_normal(self.save_path)
        except Exception as e:  # 连接超时等其他错误
            log(2, self.src, "open url failed.", e)
            if response and str(response.status_code) == '403':
                HAS_403 = True
            self.find_another_src()
        return None

    def find_another_src(self):
        """
        下载图片失败，寻找一个新的源

        :return: None
        """
        try:
            response = requests.get(self.url, headers=gen_headers(referer=self.url), timeout=60)
            ano = find_another_img(response.text)
            if '?' not in self.url:  # 第一次查找其他源
                tmp_url = self.url + '?nl=' + ano
            else:
                tmp_url = self.url + '&nl=' + ano

            response = requests.get(tmp_url, headers=gen_headers(referer=self.url), timeout=60)
            ano_src = find_img(response.text)

            self.url = tmp_url
            self.src = ano_src
        except Exception as e:
            log(2, self.url + " find another src failed.", e)
            self.try_times += 1

    def get_img_info(self):
        """
        获取dict形式的ImageInfo信息

        :return: dict形式ImageInfo信息
        """
        return self.img_info.to_dict()


class ImageInfo:
    """
    图片信息类，用以检测下载的图片是否正确
    """

    def __init__(self, url='', page_no='0'):
        """
        初始化函数。此类包含以下参数:

        - url: 图片显示的地址
        - page: 图片页码
        - download_name: 图片相对地址名称

        - name: 文件名，主要包含文件类型信息
        - width: 宽度，从页面获取
        - height: 高度，从页面获取

        - name_ori: 原图文件名，主要包含文件类型信息
        - width_ori: 原图宽度，没有原图则设置为0
        - height_ori: 原图高度，没有原图则设置为0

        :return: 类型实例
        """
        self.url = url
        self.page = page_no
        self.download_name = ''

        self.width = 0
        self.height = 0

        self.width_ori = 0
        self.height_ori = 0

    def check_ori(self, save_path):
        """
        检查原图是否下载正确，对于下载错误的图片，会删除之

        :param save_path: 图片存储地址
        :return: 正确下载返回文件名，否则None
        """
        files = [os.path.join(save_path, file) for file in glob.glob1(save_path, '{:0>3}_ori.*'.format(self.page))]
        for file in files:
            if file.endswith('gif') and os.path.getsize(file) not in [142, 143]:  # 只要不是142,143的gif，则认为其正确
                return file
            elif file.endswith('gif') or file.endswith('php'):  # 普通图及原图403后的结果
                continue
            else:
                r_width, r_height = get_img_size(file)
                if self.width_ori == r_width and self.height_ori == r_height:
                    return file
        return None

    def check_normal(self, save_path):
        """
        检查图片是否下载正确，对于下载错误的图片，会删除之

        :param save_path: 图片存储地址
        :return: 正确下载返回文件名，否则None
        """
        files = [os.path.join(save_path, file) for file in glob.glob1(save_path, '{:0>3}.*'.format(self.page))]
        for file in files:
            if file.endswith('gif') and os.path.getsize(file) not in [142, 143]:  # 只要不是142,143的gif，则认为其正确
                return file
            elif file.endswith('gif') or file.endswith('php'):  # 普通图及原图403后的结果
                continue
            else:
                r_width, r_height= get_img_size(file)
                if self.width == r_width and self.height == r_height:
                    return file
        return None

    def check_all(self, save_path):
        """
        在地址下检查所有图片是否下载完成，如果有原图，就检查原图，否则检查普通图片

        :param save_path: 保存地址
        :return: 正确下载返回文件名，否则None
        """
        return self.check_ori(save_path) if self.width_ori > 0 else self.check_normal(save_path)

    def to_dict(self):
        """
        使用一个dict存储类型所有信息

        :return: dict
        """
        result = dict()
        result['url'] = self.url
        result['page'] = self.page
        result['download_name'] = self.download_name

        result['width'] = self.width
        result['height'] = self.height

        result['width_ori'] = self.width_ori
        result['height_ori'] = self.height_ori
        return result

    @staticmethod
    def from_dict(dic):
        """
        从字典变形为一个实体类

        :param dic: 数据字典
        :return: 实体类
        """
        result = ImageInfo()
        result.url = dic['url']
        result.page = dic['page']
        result.download_name = dic['download_name']

        result.width = dic['width']
        result.height = dic['height']

        result.width_ori = dic['width_ori']
        result.height_ori = dic['height_ori']
        return result


class Dispatcher(threading.Thread):
    """
    监视线程，也负责工作的维护
    """

    def __init__(self, root_path, save_path, worker_number):
        threading.Thread.__init__(self)
        self.name = 'Dispatcher'
        self.queue = queue.Queue()
        self.root_path = root_path
        self.save_path = save_path
        self.gallery = None
        self.worker_number = worker_number

        self.done = False
        self.workers = []

    def get_basic_info(self):
        """
        生成gallery的基本信息

        :return: 是否成功
        """
        try:
            self.gallery = Gallery(self.root_path)
            tasks = self.gallery.analysis_pages(self.save_path)
            for task in tasks:
                self.queue.put(task)
            return True
        except Exception as e:  # 创建出错的话直接返回
            log(2, 'Error in creating gallery:', e)
            return False

    def run(self):
        global HAS_403

        # 创建worker
        for i in range(self.worker_number):
            self.workers.append(Worker('Worker' + str(i), self.queue, self.gallery))

        # 开始下载
        self.gallery.mkdir()
        for worker in self.workers:
            worker.start()

        while not self.done:

            awake = 0
            for worker in self.workers:
                # 查询线程工作状态
                if not worker.done:
                    awake += 1

            if self.queue.qsize() < 1 and awake == 0:
                # 当任务队列结束，并且所有线程都结束时，任务结束
                for worker in self.workers:
                    worker.stop()

                log(0, 'final check, clean dir')
                pages = 0
                for root, dirs, files in os.walk(os.path.join(self.save_path, self.gallery.name)):
                    for file in files:
                        if file in self.gallery.imgs:
                            pages += 1
                        else:
                            os.remove(os.path.join(root, file))
                undone = os.path.join(self.save_path, self.gallery.name, 'undone')
                if pages == self.gallery.length:
                    log(0, 'check right, task over')
                    if os.path.exists(undone):
                        os.remove(undone)
                else:  # 检查不成功，写一个undone文件标识此为未完成
                    log(1, 'check fail: expected:', self.gallery.length, ', real: ', str(pages), 'task Over')
                    with open(undone, 'w', encoding='utf-8') as file:
                        file.write('undone')
                self.gallery.save_dict()
                self.done = True
            if HAS_403:  # 出现403则结束任务
                log(2, '403 happened, stop dispatcher.')
                for worker in self.workers:
                    worker.stop()
                self.done = True

            time.sleep(2)


# 负责下载的工作类
class Worker(threading.Thread):
    """
    下载工作类，即一个线程
    """

    def __init__(self, name, que, gall):
        threading.Thread.__init__(self)
        self.name = name
        self.done = False  # 任务是否已完成
        self.queue = que  # 任务队列
        self.gall = gall

    def stop(self):
        """
        彻底终止此线程
        """
        self.done = True

    def run(self):
        """
        执行下载任务
        """
        global HAS_403

        while not self.done:
            try:
                task = self.queue.get(timeout=5)  # 阻塞模式，最多等待5秒
                if task.try_times > 3:
                    log(0, 'task:', task.url, 'is over tried.')
                elif HAS_403:
                    log(0, '403 happened.')
                    self.stop()
                elif task.download():  # 下载成功
                    log(0, 'download success. page:', '{:0>3}'.format(task.page), 'now queue size:', self.queue.qsize())
                    img_dic = task.get_img_info()  # 执行下载过程后才会生成图片信息
                    self.gall.imgs[img_dic['download_name']] = img_dic
                else:  # 下载失败
                    self.queue.put(task)
                    log(0, 'download failed. page:', '{:0>3}'.format(task.page), 'now queue size:', self.queue.qsize())
            except queue.Empty:  # empty即取出任务失败，没有任务可用时
                log(0, self.name, ' done!')
                self.stop()

if __name__ == '__main__':
    connect_to_exhentai('mdlovewho', 'ma199141')
    root_path = r'd:\bbb'
    for gall in os.listdir(root_path):
        now = os.path.join(root_path, gall)
        dic = os.path.join(now, 'gallery.dic')
        pkl = os.path.join(now, 'gallery.pkl')
        if os.path.exists(dic):
            with open(dic, 'rb') as file:
                d = pickle.load(file)
            disp = Dispatcher(d['root_path'], root_path, 3)
            if disp.get_basic_info():
                new = os.path.join(root_path, disp.gallery.name)
                if disp.gallery.name != gall:
                    for file in os.listdir(now):
                        os.renames(os.path.join(now, file), os.path.join(new, file))
                    dic = os.path.join(new, 'gallery.dic')
                    gall = disp.gallery.name
                disp.start()
            else:
                disp.done = True
            while not disp.done:
                time.sleep(2)
            if not os.path.exists(os.path.join(root_path, gall, 'undone')):
                if os.path.exists(dic):
                    os.remove(dic)
                os.renames(os.path.join(root_path, gall), os.path.join(r'd:\done', gall))
            if HAS_403:
                break
        elif os.path.exists(pkl):
            with open(pkl, 'rb') as file:
                d = pickle.load(file)
            disp = Dispatcher(d['root_path'], root_path, 3)
            if disp.get_basic_info():
                new = os.path.join(root_path, disp.gallery.name)
                if disp.gallery.name != gall:
                    for file in os.listdir(now):
                        os.renames(os.path.join(now, file), os.path.join(new, file))
                    dic = os.path.join(new, 'gallery.dic')
                    gall = disp.gallery.name
                disp.start()
            else:
                disp.done = True
            while not disp.done:
                time.sleep(2)
            if not os.path.exists(os.path.join(root_path, gall, 'undone')):
                if os.path.exists(dic):
                    os.remove(dic)
                os.renames(os.path.join(root_path, gall), os.path.join(r'd:\done', gall))
            if HAS_403:
                break