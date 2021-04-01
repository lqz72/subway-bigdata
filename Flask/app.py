from flask import Flask,Response,request
from flask import render_template
from flask import redirect, url_for, jsonify
from flask.json import JSONEncoder
from sys import path
import os
import json
import time
import warnings
warnings.filterwarnings('ignore')
path.append('..')
path.append(os.path.abspath(os.path.dirname(__file__)).split('Flask')[0])
path.append(os.path.abspath(os.path.dirname(__file__)).split('Flask')[0] + 'PredictModel\\')

import numpy as np
from DataAnalysis import DataApi
from MakeChart import ChartApi
from MysqlOS import SQLOS

app=Flask(__name__)
api=DataApi()

abs_path = os.path.abspath(os.path.dirname(__file__))
station_name='Sta1'

#------------模板渲染------------
@app.route('/')
def root():                             
    return redirect(url_for('index'))

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/predict')
def predict():
    return render_template('predict.html')

@app.route('/client')
def client():
    return render_template('client.html')

@app.route('/selfcenter')  
def selfcenter():
    return render_template('selfcenter.html')

@app.route('/userinf')
def userinf():
    return render_template('userinf.html')

@app.route('/history')
def history():
    return render_template('history.html')

@app.route('/aboutus')
def aboutus():
    return render_template('about-us.html')
    
@app.route('/eventdetails')
def eventdetails():
    return render_template('event-details.html')

@app.route('/log')
def log():
    return render_template('log.html')

#------------需要调用的api------------
@app.route('/sta/json')
def get_sta_json() -> json:
    with open(abs_path + '/stations.json', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/link/json')
def get_link_json() -> json:
    with open(abs_path + '/links.json', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/thisday_info', methods = ['POST', 'GET'])
def thisday_info() -> json:
    """返回指定日期天气、节假日、客流信息
    """
    curr_date = request.get_data().decode('utf-8')
    month, day = curr_date[:-3], curr_date[-2:]

    weather = SQLOS.get_weather_info(curr_date)
    is_hoilday = SQLOS.get_hoilday_info(curr_date)
    day_flow = api.month_dict[month][day]

    info_dict = {
        'weather': weather[0][0], 
        'is_hoilday': ('是' if is_hoilday[0][0] == '1' else '否'),
        'day_flow': int(day_flow),
    }

    return jsonify(info_dict)

@app.route('/sta_rank', methods=['POST', 'GET'])
def sta_rank() -> json:
    """返回站点客流排行
    """
    curr_date = request.get_data().decode('utf-8')
    sta_rank_list = api.get_top_sta(curr_date)

    return jsonify(sta_rank_list)

@app.route('/user_info', methods=['POST', 'GET'])
def user_info() -> json:
    """返回指定用户的个人信息
    """
    user_id = request.get_data().decode('utf-8')
    user_info = api.get_user_info(user_id)

    return jsonify(user_info)

@app.route('/users_info/<int:page>', methods=['POST', 'GET'])
def users_info(page) -> json:
    """根据索引返回批量用户信息
    """
    users_info_list = api.get_users_by_index(index = page)
    
    return jsonify(users_info_list)
    
@app.route('/user_record', methods=['POST', 'GET'])
def user_trip_record():
    """返回用户近期出行记录
    """
    user_id = request.get_data().decode('utf-8')
    trip_record = api.get_user_trip_record(user_id)

    return jsonify(trip_record)

@app.route('/admin_info', methods=['POST', 'GET'])
def admin_info() -> json:
    """返回管理员信息
    """
    user_list = SQLOS.get_admin_info()

    return jsonify(user_list)

@app.route('/in_hour_flow', methods = ['POST', 'GET'])
def in_hour_flow() -> json:
    """返回当前日期各站点6点-9点的进站客流量
    """
    curr_date = request.get_data().decode('utf-8')
    in_hour_dict = api.get_in_hour_flow(curr_date)

    return jsonify(in_hour_dict)

@app.route('/out_hour_flow', methods = ['POST', 'GET'])
def out_hour_flow() -> json:
    """返回当前日期各站点6点-9点的出站客流量
    """
    curr_date = request.get_data().decode('utf-8')
    out_hour_dict = api.get_out_hour_flow(curr_date)
    
    return jsonify(out_hour_dict)

@app.route('/split_flow/<int:line>', methods=['POST', 'GET'])
def split_flow(line) -> json:
    """返回地铁断面客流
    """ 
    curr_date = request.get_data().decode('utf-8')
    split_flow= api.get_line_split_flow(curr_date, '%s号线' % line)

    return jsonify(split_flow)

@app.route('/od_flow', methods=['POST', 'GET']) 
def od_flow() -> json:
    """返回OD客流
    """
    curr_date = request.get_data().decode('utf-8')
    od_flow = api.get_od_flow(curr_date)

    return jsonify(od_flow)

@app.route('/wirte_to_database', methods=['POST', 'GET'])
def add_user():
    """新增用户信息
    """
    info_json = request.get_data().decode('utf-8')
    info_dict = json.loads(info_json)
    
    username  = info_dict['username']
    pwd = info_dict['pwd']
    tips = info_dict['tips']

    res = SQLOS.add_user_to_db(username, pwd, tips)

    return str(res)

@app.route('/update_database', methods=['POST', 'GET'])
def update_user():
    """修改用户信息
    """
    info_json = request.get_data().decode('utf-8')
    info_dict = json.loads(info_json)

    index = info_dict['index']
    username  = info_dict['inf']['username']
    pwd = info_dict['inf']['pwd']
    tips = info_dict['inf']['tips']

    res = SQLOS.update_user_info(int(index), username, pwd, tips)

    return str(res)

@app.route('/del_inf', methods=['POST', 'GET'])
def del_user():
    """删除用户信息
    """
    index = request.get_data().decode('utf-8')
    res = SQLOS.del_user_info(int(index))
    
    return str(res)

#------------控制图表的展示------------
@app.route('/history/day_flow/line', methods = ['POST', 'GET'])
def day_flow():
    current_date = request.get_data().decode('utf-8')
    month = current_date[:-3] 
    month_dict = api.month_dict
    day_dict = month_dict[month]
    day_line = ChartApi.day_line(month, day_dict)

    return day_line.dump_options_with_quotes()

@app.route('/history/curr_week_flow/line', methods = ['POST', 'GET'])
def curr_week_flow():
    current_date = request.get_data().decode('utf-8')
    curr_week_dict = api.get_curr_week_flow(current_date)
    curr_week_line = ChartApi.curr_week_line(curr_week_dict)

    return curr_week_line.dump_options_with_quotes()

@app.route('/history/age/pie', methods = ['POST', 'GET'])
def age_pie():
    age, percent = api.age, api.percent
    age_pie = ChartApi.age_pie(age, percent)
    return age_pie.dump_options_with_quotes()

@app.route('/history/age/bar', methods = ['POST', 'GET'])
def age_bar():
    age, percent = api.age, api.percent
    age_bar = ChartApi.age_bar(age, percent)
    return age_bar.dump_options_with_quotes()

@app.route('/history/user_flow/line', methods = ['POST', 'GET'])
def user_flow_line():
    user_id = request.get_data().decode('utf-8')

    if user_id == '' or user_id == None:
        user_id = 'd4ec5a712f2b24ce226970a8d315dfce'

    month_dict = api.get_user_month_flow(user_id)
    flow_line = ChartApi.user_month_line(month_dict)

    return flow_line.dump_options_with_quotes()

@app.route('/history/line/pie', methods=['POST', 'GET'])
def line_pie():
    current_date = request.get_data().decode('utf-8')
    line, percent = api.get_line_flow_percent(current_date)
    pie = ChartApi.line_pie(line, percent)

    return pie.dump_options_with_quotes()


if __name__ == '__main__':
    app.run(debug=True)

