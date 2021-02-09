from flask import Flask,Response,request
from flask import render_template
from flask import redirect
from sys import path
import os
path.append('..')
path.append(os.path.abspath(os.path.dirname(__file__)).split('Flask')[0])
path.append(os.path.abspath(os.path.dirname(__file__)).split('Flask')[0] + 'PredictModel\\')
print(path)
from PredictModel import DataSource, AgeStructure, MonthFlow, StationFlow, WeekdayFlow
app=Flask(__name__)

station_name="Sta1"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/history')
def history():
    return render_template('history.html')

@app.route('/history/age')
def age():
    return render_template('age.html')

@app.route('/history/month_flow')
def month_flow():
    return render_template('wholemonth.html')

@app.route('/history/week_flow')
def week_flow():
    return render_template('week.html')

@app.route('/history/station_flow', methods = ["GET", "POST"])
def station_flow():
    global station_name
    if request.method == "POST":
        station_name = request.form.get("station_select")
    station_list = DataSource.station_list
    return render_template('station.html', station_list=station_list)

@app.route('/history/dayhigh')
def dayhigh():
    return render_template('dayhigh.html')

@app.route('/history/age/pie')
def age_pie():
    age, percent = AgeStructure.age, AgeStructure.percent
    age_pie = AgeStructure.age_pie(age, percent)
    return age_pie.dump_options_with_quotes()

@app.route('/history/month_flow/line')
def month_flow_line():
    month_line = MonthFlow.month_line(MonthFlow.month_dict)
    return month_line.dump_options_with_quotes()

@app.route('/history/week_flow/line')
def week_flow_line():
    week_line = WeekdayFlow.week_line(WeekdayFlow.week_dict)
    return week_line.dump_options_with_quotes()

@app.route('/history/station_flow/bar', methods = ["GET", "POST"])
def station_flow_bar():
    global station_name
    in_dict, out_dict = StationFlow.in_dict, StationFlow.out_dict
    bar = StationFlow.station_bar(station_name, in_dict, out_dict)
    return bar.dump_options_with_quotes()

if __name__ == '__main__':
    app.run()