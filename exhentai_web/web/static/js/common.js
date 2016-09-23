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

function getDefaultValue (val) {
	return val.length === 0 ? null : val;
}

function initFilter() {
    var filter = {}
    filter.group = ''
    filter.author = ''
    filter.tag = ''
    filter.status = 1
    return filter
}