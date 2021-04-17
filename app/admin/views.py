# admin directory views.py
# 관리자 로그인, 등록, 사용자 목록, 사용자 권한 조정, 사용자 삭제 페이지의 url을 라우팅 하는 뷰함수 python module

#from flask import ...
from . import admin

@admin.route('/')
def function_name():
    # function_name은 개발자가 지정하기.
    return '관리자 계정 메인입니다.'