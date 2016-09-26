/* 存放一些通用方法 */

// csrf相关功能，包括一个查找cookie的方法
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

function initFilter() {
    var filter = {}
    var url = window.location.href

    var group = getQueryString('group')
    filter.group = group == null ? '' : group

    var author = getQueryString('author')
    filter.author = author == null ? '' : author

    var character = getQueryString('character')
    filter.character = character == null ? '' : character

    var parody = getQueryString('parody')
    filter.parody = parody == null ? '' : parody

    var tag = getQueryString('tag')
    filter.tag = tag == null ? '' : tag

    var status = getQueryString('status')
    filter.status = status == null ? '1' : status
    return filter
}

function getQueryString(name) {
     var reg = new RegExp("(^|&)"+ name +"=([^&]*)(&|$)");
     var r = window.location.search.substr(1).match(reg);
     if(r!=null) {
        return unescape(r[2])
     }
     return null;
}

function get_base_url() {
    var urls = window.location.href.split('?')
    return urls[0]
}