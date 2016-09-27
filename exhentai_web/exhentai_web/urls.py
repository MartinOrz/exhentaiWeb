"""exhentai_web URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
import django.views.static
from exhentai_web import settings
from web import views

urlpatterns = [
    url(r'^admin/', admin.site.urls),

    # 获取画集信息
    url(r'gallery$', views.get_gallery_id, name='get_gallery_id'),
    url(r'gallery/(\d+)/$', views.method_dispatch(GET=views.get_gallery_info,
                                                  POST=views.update_gallery,
                                                  DELETE=views.delete_gallery), name='gallery'),
    url(r'^gallery/(\d+)/$', views.get_gallery_info, name='get_gallery_info'),  # 根据id获取画集信息
    url(r'^gallery/(\d+)/(\d+)/$', views.get_gallery_img, name='get_gallery_img'),  # 根据id及页码获取图片

    # 导入画集
    url(r'^import/$', views.import_galleries),

    # 作者
    url(r'^author/(\d+)/$', views.method_dispatch(GET=views.get_author), name='author'),

    # 标签
    url(r'^tag/(\d+)/$', views.method_dispatch(GET=views.get_tag,
                                                  POST=views.update_tag), name='tag'),

    # 静态文件
    url(r'^static/(?P<path>.*)$', django.views.static.serve, {'document_root':settings.STATICFILES_DIRS}),
]
