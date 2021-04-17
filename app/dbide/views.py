## dbide directory views.py
# dbms 내/외부 접속, 쿼리 실행(전공자 & 비전공자) 페이지의 url을 라우팅하는 뷰함수 python module

#from flask import ...
from flask import current_app, render_template, request, session, url_for, redirect, jsonify
from . import dbide

@dbide.route('/main')
def main():
    # function_name은 개발자가 지정하기.
    print(session)
    return 'dbide main 입니다.'