import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from scipy.optimize import minimize
from sklearn.linear_model import LassoCV, LinearRegression, RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import (GridSearchCV, TimeSeriesSplit,cross_val_score)
from sklearn.preprocessing import LabelEncoder, StandardScaler
from xgboost import XGBClassifier, XGBRegressor
from xgboost import plot_importance
import xgboost as xgb
import joblib
from sys import path
import os
import warnings
warnings.filterwarnings('ignore')

plt.rcParams['font.sans-serif'] = ['SimHei']  # 指定默认字体 SimHei为黑体
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

scaler = StandardScaler() #标准化缩放器

tscv = TimeSeriesSplit(n_splits=5)  #五折交叉验证

#数据文件路径
abs_path = os.path.abspath(os.path.dirname(__file__)) + '/csv_data/'
file_path = {
    'flow': abs_path + 'flow.csv',
    'hoilday': abs_path + 'hoilday2020.csv',
    'weather': abs_path + 'weather2020.csv',
    'feature': abs_path + 'feature2020.csv'
}

def mean_absolute_percentage_error(y_true, y_pred):
    '''
    自定义平均绝对百分误差
    '''
    return np.mean(np.abs((y_true - y_pred) / y_true)) * 100

def get_train_data():
    '''
    获取训练数据
    '''
    flow_df = pd.read_csv(file_path['flow'], encoding='gb18030')
    hoilday_df = pd.read_csv(file_path['hoilday'], encoding='gb18030', names = ['day', 'is_hoilday'])
    weather_df = pd.read_csv(file_path['weather'], encoding='gb18030')

    flow_df['y'] = 1
    flow_df = flow_df.groupby(by = ['day', 'weekday', 'month'], as_index = False)['y'].count()
    #flow_df['is_weekend'] = flow_df.weekday.isin([6,7])*1
    flow_df['day'] = flow_df['day'].apply(pd.to_datetime)
    flow_df = flow_df[flow_df['day'] >= '2020-01-01']
    flow_df.index = range(flow_df.shape[0])
    
    weather_df.drop('day', axis=1, inplace=True)
    train_df = pd.concat([flow_df, hoilday_df.is_hoilday, weather_df], axis=1)
    train_df.dropna(inplace=True)
    train_df[['weekday', 'month', 'y']] = train_df[['weekday', 'month', 'y']].astype('int')

    #增加移动平均特征  取前3个值的平均值
    def moving_avg(x):
        return sum(x.values[:-1]) / (x.shape[0] - 1)
    train_df['MA3'] = train_df.y.rolling(4).apply(moving_avg)

    #去掉最高和最低 保留二者平均
    train_df.drop(['high_temp', 'low_temp'], axis = 1, inplace = True)
    train_df.dropna(inplace=True)
    
    return train_df

def feature_coding(train_df):
    '''
    对特征进行编码
    '''
    #气温信息对于数值敏感 采用label编码 tips:弃用 气温已改为数值
    # train_df.mean_temp = LabelEncoder().fit_transform(train_df.mean_temp)

    #天气状况与数值无关 采用one-hot编码
    train_df = pd.get_dummies(train_df)

    return train_df

def train_test_split(X, y, train_size=0.9):
    '''
    划分训练集和测试集
    '''
    X_length = X.shape[0]
    split = int(X_length*train_size)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    return X_train, X_test, y_train, y_test

def plot_model_results(model, X_train, X_test, y_train, y_test, plot_intervals=False, plot_anomalies=False):  
    '''
    预测可视化
    '''
    prediction = model.predict(X_test)

    plt.figure(figsize=(15, 7))
    
    plt.plot(prediction, "g", label="prediction", linewidth=2.0)
    plt.plot(y_test.values, label="actual", linewidth=2.0)

    if plot_intervals:
        cv = cross_val_score(model, X_train, y_train, cv=tscv, scoring="neg_mean_absolute_error")
        
        #均值
        mae = cv.mean() * (-1)

        #标准差
        deviation = cv.std()

        scale = 1.96

        #上下置信区间
        lower = prediction - (mae + scale * deviation)
        upper = prediction + (mae + scale * deviation)

        plt.plot(lower, "r--", label="upper bond / lower bond", alpha=0.5)
        plt.plot(upper, "r--", alpha=0.5)

        #异常检测
        if plot_anomalies:
            anomalies = np.array([np.NaN]*len(y_test))
            anomalies[y_test<lower] = y_test[y_test<lower]
            anomalies[y_test>upper] = y_test[y_test>upper]

            plt.plot(anomalies, "o", markersize=10, label = "Anomalies")

    #平均绝对百分误差
    error = mean_absolute_percentage_error(prediction, y_test)

    plt.title("Mean absolute percentage error {0:.2f}%".format(error))
    plt.legend(loc="best")
    plt.tight_layout()
    plt.grid(True)
    plt.savefig('./predict.png')

def short_forecast(train_df, train_size):
    '''
    短期时序预测 
    '''
    train_df.set_index('day', inplace=True)
    
    X, y  = train_df.drop('y', axis = 1), train_df.y
    X_train, X_test, y_train, y_test = train_test_split(X, y, train_size)
 
    #标准化处理
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    best_param = get_best_param(X_train_scaled, y_train)

    #调用xgboost回归器
    reg = XGBRegressor(**best_param)
    reg.fit(X_train, y_train)
    prediction = reg.predict(X_test)

    plot_importance(reg)

    plot_model_results(reg, X_train=X_train, X_test=X_test, y_train=y_train
        , y_test=y_test, plot_intervals=True)

    mae = mean_absolute_error(prediction, y_test)
    mape = mean_absolute_percentage_error(prediction, y_test)
    mse = mean_squared_error(prediction, y_test)
    r2 = r2_score(prediction, y_test)
    
    joblib.dump(reg, 'test_model.pkl')
    print('mae:', mae, 'mape:', mape, 'mse:', mse, 'r2_score:', r2)
    return reg

def get_best_param(X_train, y_train):
    '''
    xgboost参数调优 返回最优参数字典
    '''
    other_params = {'eta': 0.3, 'n_estimators': 500, 'gamma': 0, 'max_depth': 6, 'min_child_weight': 1,
                'colsample_bytree': 1, 'colsample_bylevel': 1, 'subsample': 1, 'reg_lambda': 1, 'reg_alpha': 0,
                'seed': 33}

    params_dict = {
        'n_estimators':     np.linspace(100, 1000, 10, dtype=int),
        'max_depth':        np.linspace(1, 10, 10, dtype=int),
        'min_child_weight': np.linspace(1, 10, 10, dtype=int),
        'gamma':            np.linspace(0, 1, 10),
        'subsample':        np.linspace(0, 1, 11),
        'colsample_bytree': np.linspace(0, 1, 11)[1:],
        'reg_lambda':       np.linspace(0, 100, 11),
        'reg_alpha':        np.linspace(0, 10, 11),
        'learning_rate':    np.logspace(-2, 0, 10)
    }

    best_score = -0.3
    for param in params_dict:
        cv_params = {param: params_dict[param]}
 
        reg = XGBRegressor(**other_params)  #设定参数
        gs = GridSearchCV(reg, cv_params, verbose=2, refit=True, cv=5, n_jobs=-1)
        gs.fit(X_train, y_train)  # X为训练数据的特征值，y为训练数据客流量
        # 性能测评
        print("{}的最佳取值:{}".format(param, gs.best_params_[param]))
        print("最佳模型得分:", gs.best_score_)

        #更新参数字典
        if gs.best_score_ > best_score:
            best_score = gs.best_score_
            other_params[param] = gs.best_params_[param]

    print(other_params)
    return other_params

def main():
    #获取未来三个月特征值 MA3需填充
    feature_df = pd.read_csv(file_path['feature'], encoding='gb18030')
    feature_df.day = pd.to_datetime(feature_df.day)
    feature_df.set_index('day', inplace=True)
    feature_df = feature_coding(feature_df)

    feature_df = feature_df['2020-07-14':]
    #获取训练数据
    train_df = feature_coding(get_train_data())

    reg = short_forecast(train_df, train_size=0.9)
    joblib.dump(reg, 'test_model.pkl')

    #调取训练模型
    model = joblib.load('test_model.pkl')

    moving_avg = 3
    predict_list = []
    #获取预测日期之前三天的客流量 取平均值
    for i in range(7):
        index = i + moving_avg
        feature_df.MA3[index] = sum(feature_df.y.values[index - 3:index]) / moving_avg
        df = feature_df[index:index+1]
        X, y = df.drop(['y'], axis=1), df.y

        prediction = model.predict(X)[0]
        feature_df.y[index:index + 1] = prediction
        predict_list.append(prediction)
    
    print(predict_list)
     
if __name__ == '__main__':
    main()
    # train_df = get_train_data()
    # train_df.set_index('day', inplace=True)
    # train_df = feature_coding(train_df)
    # X, y  = train_df.drop('y', axis = 1), train_df.y
    # X_train, X_test, y_train, y_test = train_test_split(X, y, train_size=0.9)
    
    # get_best_param(X_train, y_train)

