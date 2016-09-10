# coding=utf-8
__author__ = 'v_mading'

# 此模块储存一些用于输入的方法

import math
import pickle
import os


def get_input():
    result = []
    inn = ''
    while inn != 'end':
        inn = input()
        result.append(inn)
    result = result[:-1]
    _dic = {}
    for res in result:
        tmp = res.split(' ')
        url = tmp[0]
        length = int(tmp[1])
        pri = int(tmp[2]) if len(tmp) == 3 else 50
        prif = pri / math.log(length)
        if prif not in _dic:
            _dic[prif] = [(url, length, pri)]
        else:
            _dic[prif].append((url, length, pri))
    result = []
    urls = {}
    for k in sorted(_dic.keys(), reverse=True):
        for u in _dic[k]:
            if u[0] not in urls:
                result.append((u[0], u[1], u[2], k))
                urls[u[0]] = 1
    return result


def resort(result):
    _dic = {}
    for k in result:
        if k[3] not in _dic:
            _dic[k[3]] = [k]
        else:
            _dic[k[3]].append(k)
        result = []
    urls = {}
    for k in sorted(_dic.keys(), reverse=True):
        for u in _dic[k]:
            if u[0] not in urls:
                result.append((u[0], u[1], u[2], k))
                urls[u[0]] = 1
    return result


def get_test():
    test = os.path.join(os.path.dirname(os.getcwd()), 'data', 'test.pkl')
    return test


def read():
    with open(get_test(), 'rb') as file:
        return pickle.load(file)


def save(result):
    with open(get_test(), 'wb') as file:
        pickle.dump(result, file)


