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
from web import views

urlpatterns = [
    url(r'^admin/', admin.site.urls),

    # 获取画集信息
    url(r'gallery/id/$', views.get_gallery_id, name='get_gallery_id'),  # 获取随机画集id

    url(r'^galleryHome$', views.image_page, name='image_page'),
    url(r'^gallery/(\d+)/$', views.get_gallery_info, name='get_gallery_info'),  # 根据id获取画集信息
    url(r'^gallery/(\d+)/(\d+)/$', views.get_gallery_img, name='get_gallery_img'),  # 根据id及页码获取图片

    # 导入画集
    url(r'^import/$', views.import_galleries),
]
