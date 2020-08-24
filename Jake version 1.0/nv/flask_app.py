# This is a Python Flask application script, created by Jake Zhang on October 6th, contains code for the famous News Vendor Game.
# This is a web test version of the game with support from sqlalchemy database and flask admin view.
# This version ask students to proceed the game together at a consistent pace and provide their rankings simultaneously.
#########################################################################################################################################

# supporting libraries
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import io
import base64
#########################################################################################################################################

# basic flask setup
from flask import Flask, request, url_for, redirect

app = Flask(__name__)


# home address
# 'http://harishk.pythonanywhere.com'
# 'localhost:5000'

# html template
def html_template(html_h1, html_body):
    body_format = '{background-color:#78be20;background-repeat:repeat;background-position:top left;background-attachment:fixed;}'
    h1_format = '{font-family:Impact, sans-serif;color:#000338;background-color:#78be20;}'
    p_format = '{background-color:#78be20;}'
    return '''<!DOCTYPE html> <html> <head> <title>News Vendor Game</title> 
              <meta name="viewport" content="width=device-width, initial-scale=1">
              <meta name="keywords" content="News Vendor, Supply Chain Management,">
              <meta name="description" content="UBC Sauder Supply Chain Management Online Tutorial Tool">
              <style> body {} h1{} p {} </style> </head> <body>
              <h1>{}</h1>
              {} </body> </html>'''.format(body_format, h1_format, p_format, html_h1, html_body)


# html template for auto refresh
def html_ar_template(html_h1, html_body, sec):
    body_format = '{background-color:#78be20;background-repeat:repeat;background-position:top left;background-attachment:fixed;}'
    h1_format = '{font-family:Impact, sans-serif;color:#000338;background-color:#78be20;}'
    p_format = '{background-color:#78be20;}'
    return '''<!DOCTYPE html> <html> <head> <title>News Vendor Game</title>
              <meta http-equiv="refresh" content="{}"> 
              <meta name="viewport" content="width=device-width, initial-scale=1">
              <meta name="keywords" content="News Vendor, Supply Chain Management,">
              <meta name="description" content="UBC Sauder Supply Chain Management Online Tutorial Tool">
              <style> body {} h1{} p {} </style> </head> <body>
              <h1>{}</h1>
              {} </body> </html>'''.format(sec, body_format, h1_format, p_format, html_h1, html_body)


#########################################################################################################################################

# login setup
from flask_login import LoginManager, UserMixin, login_user, current_user, login_required

app.config['SECRET_KEY'] = 'newsvendor_secret'

login_manager = LoginManager(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


#########################################################################################################################################

# database setup
from flask_sqlalchemy import SQLAlchemy
import sqlite3
import enum
import scipy.stats as stats

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///newsvendor_db.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# model 1: user - login information
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)  # 8-digit student code + harish(1)/tim(2) + session number (2 digit)
    pname = db.Column(db.String(25), nullable=False)
    scode = db.Column(db.String(10), nullable=False)


# enum class for distribution type
class DistributionType(enum.Enum):
    SAMPLE_POOL = 'From Sample Pool'
    NORMAL = 'From Normal Distribution'
    TRIANGULAR = 'From Triangular Distibution'
    UNIFORM = 'From Uniform Distibution'


# model 2: parameter - game setup
class Parameter(db.Model):
    par_id = db.Column(db.Integer, primary_key=True)
    scode = db.Column(db.String(10), nullable=False, unique=True)
    consistent_pace = db.Column(db.Boolean, nullable=False, default=False)
    nrounds = db.Column(db.Integer, default=10, nullable=False)
    wholesale_price = db.Column(db.Float, default=1, nullable=False)
    retail_price = db.Column(db.Float, default=4, nullable=False)
    demand_pattern = db.Column(db.Enum(DistributionType), nullable=False)
    sample_pool_input_file_name_txt = db.Column(db.String(50))
    sample_pool_number_of_past_demand_show = db.Column(db.Integer)
    distribution_all_lower_bound = db.Column(db.Integer)
    distribution_all_upper_bound = db.Column(db.Integer)
    distribution_normal_mean = db.Column(db.Float)
    distribution_normal_std = db.Column(db.Float)
    distribution_triangular_peak = db.Column(db.Float)

    __table_args__ = (
        db.CheckConstraint('parameter.nrounds >= 10'),
        db.CheckConstraint('parameter.nrounds <= 50'),
        db.CheckConstraint('parameter.wholesale_price >= 0'),
        db.CheckConstraint('parameter.retail_price > 0'),
        db.CheckConstraint('parameter.sample_pool_number_of_past_demand_show >= 0'),
        db.CheckConstraint('parameter.distribution_all_lower_bound >= 0'),
        db.CheckConstraint('parameter.distribution_all_upper_bound > 0'),
        db.CheckConstraint('parameter.distribution_normal_mean > 0'),
        db.CheckConstraint('parameter.distribution_normal_std > 0'),
        db.CheckConstraint('parameter.distribution_triangular_peak > 0'))


# deafult function for scode in Demand model
def deafult_scode():
    try:
        recent_added_par = Parameter.query.all()[-1]
    except:
        return 'Nothing in parameters table!'
    try:
        ins_name = recent_added_par.scode.split('_')[0]
        ins_code = recent_added_par.scode.split('_')[1]
        assert ins_name in ['harishk', 'timh']
        assert len(ins_code) == 2
        assert int(ins_code) > 0
        assert int(ins_code) < 100
        assert recent_added_par.retail_price > recent_added_par.wholesale_price
        return recent_added_par.scode
    except:
        return 'Invaild session code or prices!'


# deafult function for demand_past in Demand model
def default_demand_past():
    try:
        recent_added_par = Parameter.query.all()[-1]
    except:
        return 'Nothing in parameters table!'
    if recent_added_par.demand_pattern == DistributionType.SAMPLE_POOL:
        try:
            with open(recent_added_par.sample_pool_input_file_name_txt) as input_file:
                sample_all_past_str = input_file.read()
                sample_all_past_list = [int(x.strip()) for x in sample_all_past_str.split(',') if x.strip()]
                assert len(
                    sample_all_past_list) >= recent_added_par.sample_pool_number_of_past_demand_show + recent_added_par.nrounds
                sample_past_list = sample_all_past_list[0:recent_added_par.sample_pool_number_of_past_demand_show]
                sample_past = str(sample_past_list)[1:-1]
            return sample_past
        except:
            return 'Invaild sample pool input txt file!'
    else:
        return 'N/A'


# deafult function for demand_new in Demand model
def default_demand_new():
    try:
        recent_added_par = Parameter.query.all()[-1]
    except:
        return 'Nothing in parameters table!'
    if recent_added_par.demand_pattern == DistributionType.SAMPLE_POOL:
        try:
            with open(recent_added_par.sample_pool_input_file_name_txt) as input_file:
                sample_all_new_str = input_file.read()
                sample_all_new_list = [int(x.strip()) for x in sample_all_new_str.split(',') if x.strip()]
                assert len(
                    sample_all_new_list) >= recent_added_par.sample_pool_number_of_past_demand_show + recent_added_par.nrounds
                sample_new_list = sample_all_new_list[
                                  recent_added_par.sample_pool_number_of_past_demand_show:recent_added_par.sample_pool_number_of_past_demand_show + recent_added_par.nrounds]
                sample_new = str(sample_new_list)[1:-1]
            return sample_new
        except:
            return 'Invaild sample pool input txt file!'
    else:
        if recent_added_par.demand_pattern == DistributionType.NORMAL:
            try:
                assert recent_added_par.distribution_all_upper_bound > recent_added_par.distribution_all_lower_bound
                mu = recent_added_par.distribution_normal_mean
                assert mu > recent_added_par.distribution_all_lower_bound
                assert mu < recent_added_par.distribution_all_upper_bound
                sigma = recent_added_par.distribution_normal_std
                rvs_normal = stats.truncnorm((recent_added_par.distribution_all_lower_bound - mu) / sigma,
                                             (recent_added_par.distribution_all_upper_bound - mu) / sigma, loc=mu,
                                             scale=sigma)
                generated_normal = rvs_normal.rvs(recent_added_par.nrounds)
                return str([int(round(x)) for x in generated_normal])[1:-1]
            except:
                return 'Invalid parameters for normal distribution!'
        elif recent_added_par.demand_pattern == DistributionType.TRIANGULAR:
            try:
                assert recent_added_par.distribution_all_upper_bound > recent_added_par.distribution_all_lower_bound
                assert recent_added_par.distribution_triangular_peak > recent_added_par.distribution_all_lower_bound
                assert recent_added_par.distribution_triangular_peak < recent_added_par.distribution_all_upper_bound
                generated_triangular = np.random.triangular(recent_added_par.distribution_all_lower_bound,
                                                            recent_added_par.distribution_triangular_peak,
                                                            recent_added_par.distribution_all_upper_bound,
                                                            recent_added_par.nrounds)
                return str([int(round(x)) for x in generated_triangular])[1:-1]
            except:
                return 'Invalid parameters for triangular distribution!'
        else:  # recent_added_par.demand_pattern == DistributionType.UNIFORM
            try:
                assert recent_added_par.distribution_all_upper_bound > recent_added_par.distribution_all_lower_bound
                generated_uniform = np.random.randint(recent_added_par.distribution_all_lower_bound,
                                                      recent_added_par.distribution_all_upper_bound,
                                                      recent_added_par.nrounds)
                return str([int(round(x)) for x in generated_uniform])[1:-1]
            except:
                return 'Invalid parameters for uniform distribution!'

            # model 3 demand - generated demand amount for each round


class Demand(db.Model):
    demand_id = db.Column(db.Integer, primary_key=True)
    scode = db.Column(db.String(10), nullable=False, default=deafult_scode, unique=True)
    demand_past = db.Column(db.String(300), nullable=False, default=default_demand_past)
    demand_new = db.Column(db.String(300), nullable=False, default=default_demand_new)


# model 4 game - gmae record
class Game(db.Model):
    record_id = db.Column(db.Integer, primary_key=True)
    scode = db.Column(db.String(10), nullable=False)
    id = db.Column(db.Integer, nullable=False)
    pname = db.Column(db.String(25), nullable=False)
    day_index = db.Column(db.Integer, nullable=False)
    norder = db.Column(db.Integer, nullable=False)
    ndemand = db.Column(db.Integer, nullable=False)
    nsold = db.Column(db.Integer, nullable=False)
    nlost = db.Column(db.Integer, nullable=False)
    rev = db.Column(db.Float, nullable=False)
    cost = db.Column(db.Float, nullable=False)
    profit = db.Column(db.Float, nullable=False)
    total_profit = db.Column(db.Float, nullable=False)
    round_rank = db.Column(db.Integer, default=-1, nullable=False)
    total_rank = db.Column(db.Integer, default=-1, nullable=False)


# deafult function for scode in Pace model
def deafult_pace_scode():
    try:
        recent_added_par_pace = Parameter.query.all()[-1]
        assert Demand.query.filter_by(scode=recent_added_par_pace.scode).all()
    except:
        return 'Complete Parameter or Demand table first!'
    if recent_added_par_pace.consistent_pace:
        return recent_added_par_pace.scode
    else:
        return 'This is not a consistent pace session!'


# deafult function for default_session_size in Pace model
def default_session_size():
    try:
        recent_added_par_pace = Parameter.query.all()[-1]
        assert Demand.query.filter_by(scode=recent_added_par_pace.scode).all()
        recent_added_user_count_pace = len(User.query.filter_by(scode=recent_added_par_pace.scode).all())
    except:
        return 'Complete Parameter or Demand table first!'
    if recent_added_par_pace.consistent_pace:
        return recent_added_user_count_pace
    else:
        return 'This is not a consistent pace session!'


# deafult function for default_session_id_collection in Pace model
def default_session_id_collection():
    try:
        recent_added_par_pace = Parameter.query.all()[-1]
        assert Demand.query.filter_by(scode=recent_added_par_pace.scode).all()
        recent_added_user_collection_pace = [x[0] for x in User.query.with_entities(User.id).filter_by(
            scode=recent_added_par_pace.scode).all()]
    except:
        return 'Complete Parameter or Demand table first!'
    if recent_added_par_pace.consistent_pace:
        return str(recent_added_user_collection_pace)[1:-1]
    else:
        return 'This is not a consistent pace session!'


# model 5 pace - record information for consistent pace game sessions
class Pace(db.Model):
    demand_id = db.Column(db.Integer, primary_key=True)
    scode = db.Column(db.String(10), nullable=False, default=deafult_pace_scode, unique=True)
    session_size = db.Column(db.Integer, nullable=False, default=default_session_size)
    session_id_collection = db.Column(db.String(3000), nullable=False, default=default_session_id_collection)


#########################################################################################################################################

# admin setup
from flask_admin import Admin, expose, BaseView
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.fileadmin import FileAdmin
import os

admin = Admin(app, name='Instructor Page')


class MemoView(BaseView):
    @expose('/')
    def index(self):
        return self.render('admin/memo.html')

    def is_accessible(self):
        try:
            return current_user.id in [10000001100, 10000002200, 10000003300]
        except:
            return False


admin.add_view(MemoView(name='Memo'))


class ParameterView(ModelView):
    column_display_pk = True
    column_hide_backrefs = False
    column_filters = ['scode']

    def is_accessible(self):
        try:
            return current_user.id in [10000001100, 10000002200, 10000003300]
        except:
            return False


admin.add_view(ParameterView(Parameter, db.session))


class MyFileAdmin(FileAdmin):
    def is_accessible(self):
        try:
            return current_user.id in [10000001100, 10000002200, 10000003300]
        except:
            return False


admin.add_view(MyFileAdmin(os.getcwd(), name='Files'))


class DemandView(ModelView):
    column_display_pk = True
    column_hide_backrefs = False
    column_filters = ['scode']

    def is_accessible(self):
        try:
            return current_user.id in [10000001100, 10000002200, 10000003300]
        except:
            return False


admin.add_view(DemandView(Demand, db.session))


class PaceView(ModelView):
    column_display_pk = True
    column_hide_backrefs = False
    column_filters = ['scode']

    def is_accessible(self):
        try:
            return current_user.id in [10000001100, 10000002200, 10000003300]
        except:
            return False


admin.add_view(PaceView(Pace, db.session))


class UserView(ModelView):
    column_display_pk = True
    column_hide_backrefs = False
    column_filters = ['id', 'pname', 'scode']

    def is_accessible(self):
        try:
            return current_user.id in [10000001100, 10000002200, 10000003300]
        except:
            return False


admin.add_view(UserView(User, db.session))


class GameView(ModelView):
    column_display_pk = True
    column_hide_backrefs = False
    column_filters = ['record_id', 'scode', 'id', 'pname', 'day_index', 'norder', 'ndemand', 'nsold', 'nlost', 'rev',
                      'cost', 'profit', 'total_profit']

    def is_accessible(self):
        try:
            return current_user.id in [10000001100, 10000002200, 10000003300]
        except:
            return False


admin.add_view(GameView(Game, db.session))


#########################################################################################################################################

# supporting functions

# show accumulated game stats in plot at the end of each day
def show_plot_stats_html(resdf, day_index):
    # get data from df
    day_data = list(resdf['Day #'])
    order_data = list(resdf['Order Placed'])
    demand_data = list(resdf['Customer Demand'])
    profit_data = list(resdf['Profit'])
    # start of plot
    # left ax
    sauder_green = (120 / 255, 190 / 255, 32 / 255)
    fig, ax1 = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(sauder_green)
    ax1.set_facecolor(sauder_green)
    ax1.set_xlabel('Days')
    ax1.set_ylabel('Qty', color='black')
    l1, = ax1.plot(day_data, order_data, marker='o', color='purple', linewidth=1, label='Order Qty')
    l2, = ax1.plot(day_data, demand_data, marker='o', color='red', linewidth=1, label='Demand Qty')
    ax1.tick_params(axis='y', labelcolor='black')
    # right ax
    ax2 = ax1.twinx()
    ax2.set_ylabel('Profit', color='blue')
    l3, = ax2.plot(day_data, profit_data, marker='o', color='blue', linewidth=1, label='Profit')
    ax2.tick_params(axis='y', labelcolor='blue')
    plt.xticks(np.arange(1, day_index + 1, 1))
    plt.legend([l1, l2, l3], ['Order Qty', 'Demand Qty', 'Profit'], bbox_to_anchor=(1.15, 1), loc=2, frameon=False,
               facecolor=sauder_green)
    fig.tight_layout()
    # figure to html
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
    img.seek(0)
    encoded = base64.b64encode(img.getvalue())
    fig_html = '<img src="data:image/png;base64, {}">'.format(encoded.decode('utf-8'))
    return fig_html


#########################################################################################################################################

# start of flask web app

# welcome page
# ask user to choose between sign up (first-time user) or sign in (continue previous game)
@app.route('/', methods=['GET', 'POST'])
def welcome():
    html_h1 = 'Welcome to the News Vendor Game!'
    html_body = '''
                <br />
                <p>Sign-up (for first-time user) or Sign-in (to continue previous game):
                <form action="/signup" method="get">
                <p><button type="submit" style="width:120px;height:40px;">Sign Up</button></p> 
                </form>
                <form action="/signin" method="get">
                <p><button type="submit" style="width:120px;height:40px;">Sign In</button></p> 
                </form>
                  '''
    return html_template(html_h1, html_body)


# sign up page - get
# sign up using UBC student number, preferred name, game session code, and add sign up information into db
@app.route('/signup', methods=['GET'])
def signup_get():
    html_h1 = 'Sign-up for the News Vendor Game'
    html_body = '''
                <br />
                <form action="/signup" method="post">
                <table>
                <tr>
                <td align="left">Please enter your 8-digit student code: </td>
                <td align="left"><input name="id" type="number" min="10000000" step="1" max="99999999" required /></td>
                </tr>
                <tr>
                <td align="left">Please enter your preferred name: </td>
                <td align="left"><input name="pname" type="text" minlength="1" maxlength="25" required /></td>
                </tr>
                <tr>
                <td align="left">Please enter session code provided by instructor: </td>
                <td align="left"><input name="scode" type="text" minlength="1" maxlength="10" required /></td>
                </tr>
                </table>
                <p><button type="submit" style="width:120px;height:40px;">Sign Up</button></p>
                </form>'''
    return html_template(html_h1, html_body)


# sign up page - post
# check if information is already in db then add into db
@app.route('/signup', methods=['POST'])
def signup_post():
    try:
        ubc_id = int(request.form['id'])
        pname = str(request.form['pname'])
        scode = str(request.form['scode'])
        # protect from user signing up with session code that doesn't exist
        scode_exist_par = Parameter.query.filter_by(scode=scode).all()
        scode_exist_demand = Demand.query.filter_by(scode=scode).all()
        if len(scode_exist_par) == 0 or len(scode_exist_demand) == 0:
            raise Exception('Session code doesn\'t exist!')
        temp_session_code = scode.split('_')
        if temp_session_code[0] == 'harishk':
            id = int(str(ubc_id) + '1' + temp_session_code[1])
        elif temp_session_code[0] == 'timh':
            id = int(str(ubc_id) + '2' + temp_session_code[1])
        elif temp_session_code[0] == 'jakez':
            id = int(str(ubc_id) + '3' + temp_session_code[1])
        else:
            raise Exception('Instructor name or session code error!')
        user = User(id=id, pname=pname, scode=scode)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        html_h1 = 'Sign-up successful, {}!'.format(current_user.pname)
        html_body = '''
                    <br />
                    <form action="/run" method="get">
                    <p><button type="submit" style="width:120px;height:40px;">Start</button></p> 
                    </form>'''
        return html_template(html_h1, html_body)
    except:
        html_h1 = 'Sign-up failed: wrong information or user already exist!'
        html_body = '''
                    <br />
                    <form action="/signup" method="get">
                    <p><button type="submit" style="width:120px;height:40px;">Try Again</button></p> 
                    </form>
                    <form action="/signin" method="get">
                    <p><button type="submit" style="width:120px;height:40px;">Sign In</button></p> 
                    </form>
                    '''
        return html_template(html_h1, html_body)


# sign in page - get
# sign in using UBC student number, game session code, and check sign in information exist in db
@app.route('/signin', methods=['GET'])
def signin_get():
    html_h1 = 'Sign-in for the News Vendor Game'
    html_body = '''
                <br />
                <form action="/signin" method="post">
                <table>
                <tr>
                <td align="left">Please enter your 8-digit student code: </td>
                <td align="left"><input name="id" type="number" min="10000000" step="1" max="99999999" required /></td>
                </tr>
                <tr>
                <td align="left">Please enter session code provided by instructor: </td>
                <td align="left"><input name="scode" type="text" minlength="1" maxlength="10" required /></td>
                </tr>
                </table>
                <p><button type="submit" style="width:120px;height:40px;">Sign In</button></p>
                </form>'''
    return html_template(html_h1, html_body)


# sign in page - post
# check if information is already in db then extract user information from db
@app.route('/signin', methods=['POST'])
def signin_post():
    try:
        ubc_id = int(request.form['id'])
        scode = str(request.form['scode'])
        temp_session_code = scode.split('_')
        if temp_session_code[0] == 'harishk':
            id = int(str(ubc_id) + '1' + temp_session_code[1])
        elif temp_session_code[0] == 'timh':
            id = int(str(ubc_id) + '2' + temp_session_code[1])
        elif temp_session_code[0] == 'jakez':
            id = int(str(ubc_id) + '3' + temp_session_code[1])
        else:
            raise Exception('Instructor name or session code error!')
        user = User.query.filter_by(id=id).first()
        if user:
            login_user(user)
            html_h1 = 'Sign-in successful, {}!'.format(current_user.pname)
            html_body = '''
                        <br />
                        <form action="/stats" method="get">
                        <p><button type="submit" style="width:120px;height:40px;">Continue</button></p> 
                        </form>'''

            return html_template(html_h1, html_body)
        else:
            raise Exception('Sign-in Information doesn\'t exist!')
    except:
        html_h1 = 'Sign-in failed: wrong information or user doesn\'t exist!'
        html_body = '''
                    <br />
                    <form action="/signin" method="get">
                    <p><button type="submit" style="width:120px;height:40px;">Try Again</button></p> 
                    </form>
                    <form action="/signup" method="get">
                    <p><button type="submit" style="width:120px;height:40px;">Sign Up</button></p> 
                    </form>
                    '''
        return html_template(html_h1, html_body)


# instructor login page - get
# provide a seperate page for instructors to login and access to admin page
@app.route('/instructor', methods=['GET'])
def ins_login_get():
    html_h1 = 'Instructor Login'
    html_body = '''
                <br />
                <form action="/instructor" method="post">
                <table>
                <tr>
                <td align="left">Please enter instructor ID: </td>
                <td align="left"><input name="insid" type="number" min="10000000" step="1" max="99999999" required /></td>
                </tr>
                <tr>
                <td align="left">Please enter default instructor session code : </td>
                <td align="left"><input name="insscode" type="text" minlength="1" maxlength="10" required /></td>
                </tr>
                </table>
                <p><button type="submit" style="width:120px;height:40px;">Login</button></p>
                </form>'''
    return html_template(html_h1, html_body)


# instructor login page - post
# check if instructor information is in db and then login
@app.route('/instructor', methods=['POST'])
def ins_login_post():
    try:
        ubc_id = int(request.form['insid'])
        scode = str(request.form['insscode'])
        temp_session_code = scode.split('_')
        if temp_session_code[0] == 'harishk':
            id = int(str(ubc_id) + '1' + temp_session_code[1])
        elif temp_session_code[0] == 'timh':
            id = int(str(ubc_id) + '2' + temp_session_code[1])
        elif temp_session_code[0] == 'jakez':
            id = int(str(ubc_id) + '3' + temp_session_code[1])
        else:
            raise Exception('Instructor name or session code error!')
        user = User.query.filter_by(id=id).first()
        if user and user.id in [10000001100, 10000002200, 10000003300]:
            login_user(user)
            html_h1 = 'Instructor {} login successful!'.format(current_user.pname)
            html_body = '''
                        <br />
                        <form action="/admin" method="get">
                        <p><button type="submit" style="width:120px;height:40px;">Instructor Page</button></p> 
                        </form>'''

            return html_template(html_h1, html_body)
        else:
            raise Exception('Sign-in Information doesn\'t exist!')
    except:
        html_h1 = 'Login failed: wrong information or instructor doesn\'t exist!'
        html_body = '''
                    <br />
                    <form action="/instructor" method="get">
                    <p><button type="submit" style="width:120px;height:40px;">Try Again</button></p> 
                    </form>
                    <form action="/" method="get">
                    <p><button type="submit" style="width:120px;height:40px;">Home Page</button></p>
                    </form>
                    '''
        return html_template(html_h1, html_body)


# game run page 1
# ask for order size
@app.route('/run', methods=['GET'])
@login_required
def day_start():
    # protect from instructors accessing this page
    if current_user.id in [10000001100, 10000002200, 10000003300]:
        return redirect('/admin')
    # extract info
    day_index = len(Game.query.filter_by(id=current_user.id).all()) + 1
    current_par = Parameter.query.filter_by(scode=current_user.scode).all()[-1]
    current_demand = Demand.query.filter_by(scode=current_user.scode).all()[-1]
    # redirect consistent pace users
    if current_par.consistent_pace:
        return redirect('/paceloading')
    # protect from finished user coming back and make new orders
    if day_index > current_par.nrounds:
        return redirect(url_for('game_end'))

    # flask template
    html_h1 = 'Start of Day {}!'.format(day_index)
    html_body = '''
                <br />
                <p>Number of Rounds: {}</p>
                <p>Unit Wholesale Price: ${:.2f}</p>
                <p>Unit Retail Price: ${:.2f}</p>
                <p><strong>Demand Pattern: {} {distri_null}</strong></p>
                {history}
                {previous}
                {demand_range}
                {demand_mean}
                {demand_std}
                {demand_peak}
                <br />
                <form action="/run" method="post">
                <p>Please enter number of inventory ordered for day {day}: 
                <input name="norder" type="number" min="{min}" step="1" max="{max}">
                </p>
                <p><button type="submit" style="width:120px;height:40px;">Confirm Order</button></p>
                </form>
                '''.format(int(current_par.nrounds),
                           round(float(current_par.wholesale_price), 2),
                           round(float(current_par.retail_price), 2),
                           'FROM ' + str(current_par.demand_pattern).split('.')[1].replace('_', ' '),
                           distri_null='' if current_par.demand_pattern == DistributionType.SAMPLE_POOL else 'DISTRIBUTION',
                           history='<p>Historical Demand Samples: {}</p>'.format(
                               current_demand.demand_past) if current_par.demand_pattern == DistributionType.SAMPLE_POOL else '',
                           previous='<p>Demands From Previous Rounds: {}</p>'.format(
                               str([int(x) for x in current_demand.demand_new.split(',')][:day_index - 1])[
                               1:-1]) if current_par.demand_pattern == DistributionType.SAMPLE_POOL else '',
                           demand_range='' if current_par.demand_pattern == DistributionType.SAMPLE_POOL else '<p>Demand Range: {}</p>'.format(
                               str(current_par.distribution_all_lower_bound) + ' to ' + str(
                                   current_par.distribution_all_upper_bound)),
                           demand_mean='<p>Demand Mean: {}</p>'.format(
                               current_par.distribution_normal_mean) if current_par.demand_pattern == DistributionType.NORMAL else '',
                           demand_std='<p>Demand Standard Deviation: {}</p>'.format(
                               current_par.distribution_normal_std) if current_par.demand_pattern == DistributionType.NORMAL else '',
                           demand_peak='<p>Demand Peak: {}</p>'.format(
                               current_par.distribution_triangular_peak) if current_par.demand_pattern == DistributionType.TRIANGULAR else '',
                           day=day_index, min=0, max=10000)
    return html_template(html_h1, html_body)


# game run page 2
# show result based on inventory ordered
@app.route('/run', methods=['POST'])
@login_required
def day_end():
    # extract and calculate info
    day_index = len(Game.query.filter_by(id=current_user.id).all()) + 1
    current_par = Parameter.query.filter_by(scode=current_user.scode).all()[-1]
    current_demand = Demand.query.filter_by(scode=current_user.scode).all()[-1]
    norder = int(request.form['norder'])
    ndemand = int(current_demand.demand_new.split(',')[day_index - 1])
    nsold = min(norder, ndemand)
    nlost = max(0, ndemand - norder)
    rev = round(nsold * round(float(current_par.retail_price), 2), 2)
    cost = round(norder * round(float(current_par.wholesale_price), 2), 2)
    profit = round(rev - cost, 2)
    if day_index == 1:
        total_profit = round(profit, 2)
    else:
        total_profit = round(
            profit + Game.query.filter_by(id=current_user.id, day_index=day_index - 1).first().total_profit, 2)
    # insert into db
    current_game_rec = Game(scode=current_user.scode,
                            id=current_user.id,
                            pname=current_user.pname,
                            day_index=day_index,
                            norder=norder,
                            ndemand=ndemand,
                            nsold=nsold,
                            nlost=nlost,
                            rev=rev,
                            cost=cost,
                            profit=profit,
                            total_profit=total_profit)
    db.session.add(current_game_rec)
    db.session.commit()
    # flask template
    html_h1 = 'End of Day {}!'.format(day_index)
    html_body = '''
                <br />
                <p>Inventory on hands today: {}</p>
                <p><strong>Demands today ends up to be: {}</strong></p>
                <p>Number of units sold today: {}</p>
                <p>Lost sales in units today: {}</p>
                <p>Revenue today: ${:.2f}</p>
                <p>Cost today: ${:.2f}</p>
                <p>Profit Calculation: ${:.2f} * Min(Quantity, Customer Demand) - ${:.2f} * (Quantity)</p>
                <p>Profit today: ${:.2f}</p>
                <p>Total profit: ${:.2f}</p>
                <br />
                <form action="/stats" method="get">
                <p><button type="submit" style="width:120px;height:40px;">Continue to Stats</button></p>
                </form>
                '''.format(norder, ndemand, nsold, nlost, rev, cost,
                           current_par.retail_price, current_par.wholesale_price, profit, total_profit)
    return html_template(html_h1, html_body)


# show game stats page
# show overall stats (table & plot) of the game at the end of each day
@app.route('/stats', methods=['GET', 'POST'])
@login_required
def show_stats():
    # protect from instructors accessing this page
    if current_user.id in [10000001100, 10000002200, 10000003300]:
        return redirect('/admin')
    # extract info
    day_index = len(Game.query.filter_by(id=current_user.id).all())
    current_par = Parameter.query.filter_by(scode=current_user.scode).all()[-1]
    # redirect consistent pace users
    if current_par.consistent_pace:
        return redirect('/paceloading')
    # protect from new user visiting this page before make any decision 
    if day_index == 0:
        return redirect(url_for('day_start'))

    # db to df
    db_connect = sqlite3.connect('newsvendor_db.db')
    resdf = pd.read_sql_query('''SELECT day_index,norder,ndemand,nsold,nlost,profit,total_profit
                                 FROM game
                                 WHERE id = {}'''.format(current_user.id), db_connect)
    resdf = resdf.rename(
        columns={'day_index': 'Day #', 'norder': 'Order Placed', 'ndemand': 'Customer Demand', 'nsold': 'Sold',
                 'nlost': 'Lost Sales', 'profit': 'Profit', 'total_profit': 'Total Profit'})

    # df to plot
    # conduct in function show_plot_stats_html(resdf)

    # flask template
    html_h1 = 'Accumulated Game Stats at The End of Day {}'.format(day_index)
    html_body_end = '''
                {}
                <br />
                {}
                <br />
                <form action="/end" method="get">
                <p><button type="submit" style="width:120px;height:40px;">End of Game</button></p>
                </form>
                '''.format(resdf.to_html(index=False), show_plot_stats_html(resdf, day_index))
    html_body_run = '''
                {}
                <br />
                {}
                <br />
                <form action="/run" method="get">
                <p><button type="submit" style="width:120px;height:40px;">Go to Day {}</button></p>
                </form>
                '''.format(resdf.to_html(index=False), show_plot_stats_html(resdf, day_index), day_index + 1)
    if day_index == current_par.nrounds:
        return html_template(html_h1, html_body_end)
    else:  # day_index < current_par.nrounds
        return html_template(html_h1, html_body_run)

    # show game conclusion page


# ask if user want to go back to stats and check results
@app.route('/end', methods=['GET', 'POST'])
@login_required
def game_end():
    # protect from instructors accessing this page
    if current_user.id in [10000001100, 10000002200, 10000003300]:
        return redirect('/admin')
    # extract info
    day_index = len(Game.query.filter_by(id=current_user.id).all())
    current_par = Parameter.query.filter_by(scode=current_user.scode).all()[-1]
    # redirect consistent pace users
    if current_par.consistent_pace:
        return redirect('/paceloading')
    # protect from users accessing this page until they are done (day_index = nrounds)
    if day_index < current_par.nrounds:
        return redirect(url_for('show_stats'))
    # flask template
    html_h1 = 'Well done, {}! Thanks for playing!'.format(current_user.pname)
    html_body = '''
                <br />
                <form action="/stats" method="get">
                <p><button type="submit" style="width:120px;height:40px;">Back to Stats</button></p> <form/>
                '''
    return html_template(html_h1, html_body)


#########################################################################################################################################

# start of flask web app for consistent pace game sessions

# show paced game loading page
# students will be directed to this page after login untill instructor starts the game session in Pace tab
@app.route('/paceloading', methods=['GET', 'POST'])
@login_required
def pace_loading():
    # protect from instructors accessing this page
    if current_user.id in [10000001100, 10000002200, 10000003300]:
        return redirect('/admin')
    # users for unpaced sessions are not allowed
    current_par = Parameter.query.filter_by(scode=current_user.scode).all()[-1]
    if not current_par.consistent_pace:
        return redirect('/stats')
    # users for paced sessions are allowed but returns depend on conditions
    try:
        # instructor not yet opened the paced session if exception raised
        current_pace = Pace.query.filter_by(scode=current_user.scode).all()[-1]
        # id in collection 
        if current_user.id in [int(x) for x in current_pace.session_id_collection.split(',')]:
            html_h1_2 = 'Now your game session is opened!'
            html_body_2 = '''
                           <br />
                           <h4>Reminder 1: please DO NOT use tab BACKWARDS button in your browser to go back to previous tabs or REFRESH/CLOSE tabs during game session</h4>
                           <h4>Reminder 2: you will be automatically redirected to next page in 1 minute - redirect now by click the button below</h4>
                           <form id="startform" name="startform" action="/pacerun" method="get">
                           <p><button type="submit" style="width:120px;height:40px;">Start Game</button></p> <form/>
                           <script type="text/javascript">
                           {jsfunction}
                           </script>
                           '''.format(
                jsfunction="window.onload=function(){window.setTimeout('document.startform.submit()', 60000)}")
            return html_template(html_h1_2, html_body_2)
        else:  # id not in collection
            html_h1_3 = 'Instructor has already opened the current game session! Please wait for the next session or inform instructor for assist...'
            html_body_3 = ''
            return html_template(html_h1_3, html_body_3)
    except:
        # flask template
        html_h1_1 = 'Instructor has not opened your game session yet! Please wait...'
        html_body_1 = ''
        return html_ar_template(html_h1_1, html_body_1, 5)


# paced game run page 1
# ask for order size
@app.route('/pacerun', methods=['GET'])
@login_required
def pace_day_start():
    # protect from instructors accessing this page
    if current_user.id in [10000001100, 10000002200, 10000003300]:
        return redirect('/admin')
    # extract info
    day_index = len(Game.query.filter_by(id=current_user.id).all()) + 1
    current_par = Parameter.query.filter_by(scode=current_user.scode).all()[-1]
    current_demand = Demand.query.filter_by(scode=current_user.scode).all()[-1]
    # users for unpaced sessions are not allowed
    if not current_par.consistent_pace:
        return redirect('/stats')
    # users for paced sessions are allowed but returns depend on conditions
    try:
        # instructor not yet opened the paced session if exception raised
        current_pace = Pace.query.filter_by(scode=current_user.scode).all()[-1]
        # id in collection 
        if current_user.id in [int(x) for x in current_pace.session_id_collection.split(',')]:
            pass
        else:  # id not in collection
            return redirect('/paceloading')
    except:
        return redirect('/paceloading')
    # pace control
    if day_index - 1 != min([len(Game.query.filter_by(id=y).all()) for y in
                             [int(x) for x in current_pace.session_id_collection.split(',')]]):
        return redirect('/pacewaiting')
    # protect from finished user coming back and make new orders
    if day_index > current_par.nrounds:
        return redirect(url_for('pace_game_end'))
    # flask template
    html_h1 = 'Start of Day {}!'.format(day_index)
    html_body = '''
                <h4>Reminder: default order amount (0) will be automatically submitted if you don't update and confirm your order in 2 minutes</h4>
                <br />
                <p>Number of Rounds: {}</p>
                <p>Unit Wholesale Price: ${:.2f}</p>
                <p>Unit Retail Price: ${:.2f}</p>
                <p><strong>Demand Pattern: {} {distri_null}</strong></p>
                {history}
                {previous}
                {demand_range}
                {demand_mean}
                {demand_std}
                {demand_peak}
                <br />
                <form id="orderform" name="orderform" action="/pacerun" method="post">
                <p>Please enter number of inventory ordered for day {day}: 
                <input name="norder" type="number" value="0" min="{min}" step="1" max="{max}">
                </p>
                <p><button type="submit" style="width:120px;height:40px;">Confirm Order</button></p>
                </form>
                <script type="text/javascript">
                {jsfunction}
                </script>
                '''.format(int(current_par.nrounds),
                           round(float(current_par.wholesale_price), 2),
                           round(float(current_par.retail_price), 2),
                           'FROM ' + str(current_par.demand_pattern).split('.')[1].replace('_', ' '),
                           distri_null='' if current_par.demand_pattern == DistributionType.SAMPLE_POOL else 'DISTRIBUTION',
                           history='<p>Historical Demand Samples: {}</p>'.format(
                               current_demand.demand_past) if current_par.demand_pattern == DistributionType.SAMPLE_POOL else '',
                           previous='<p>Demands From Previous Rounds: {}</p>'.format(
                               str([int(x) for x in current_demand.demand_new.split(',')][:day_index - 1])[
                               1:-1]) if current_par.demand_pattern == DistributionType.SAMPLE_POOL else '',
                           demand_range='' if current_par.demand_pattern == DistributionType.SAMPLE_POOL else '<p>Demand Range: {}</p>'.format(
                               str(current_par.distribution_all_lower_bound) + ' to ' + str(
                                   current_par.distribution_all_upper_bound)),
                           demand_mean='<p>Demand Mean: {}</p>'.format(
                               current_par.distribution_normal_mean) if current_par.demand_pattern == DistributionType.NORMAL else '',
                           demand_std='<p>Demand Standard Deviation: {}</p>'.format(
                               current_par.distribution_normal_std) if current_par.demand_pattern == DistributionType.NORMAL else '',
                           demand_peak='<p>Demand Peak: {}</p>'.format(
                               current_par.distribution_triangular_peak) if current_par.demand_pattern == DistributionType.TRIANGULAR else '',
                           day=day_index, min=0, max=10000,
                           jsfunction="window.onload=function(){window.setTimeout('document.orderform.submit()', 120000)}")
    return html_template(html_h1, html_body)


# paced game run page 2
# show result based on inventory ordered
@app.route('/pacerun', methods=['POST'])
@login_required
def pace_day_end():
    # extract and calculate info
    day_index = len(Game.query.filter_by(id=current_user.id).all()) + 1
    current_par = Parameter.query.filter_by(scode=current_user.scode).all()[-1]
    current_demand = Demand.query.filter_by(scode=current_user.scode).all()[-1]
    norder = int(request.form['norder'])
    ndemand = int(current_demand.demand_new.split(',')[day_index - 1])
    nsold = min(norder, ndemand)
    nlost = max(0, ndemand - norder)
    rev = round(nsold * round(float(current_par.retail_price), 2), 2)
    cost = round(norder * round(float(current_par.wholesale_price), 2), 2)
    profit = round(rev - cost, 2)
    if day_index == 1:
        total_profit = round(profit, 2)
    else:
        total_profit = round(
            profit + Game.query.filter_by(id=current_user.id, day_index=day_index - 1).first().total_profit, 2)
    # insert into db
    current_game_rec = Game(scode=current_user.scode,
                            id=current_user.id,
                            pname=current_user.pname,
                            day_index=day_index,
                            norder=norder,
                            ndemand=ndemand,
                            nsold=nsold,
                            nlost=nlost,
                            rev=rev,
                            cost=cost,
                            profit=profit,
                            total_profit=total_profit,
                            round_rank=0,
                            total_rank=0)
    db.session.add(current_game_rec)
    db.session.commit()
    # flask template
    html_h1 = 'End of Day {}!'.format(day_index)
    html_body = '''
                <br />
                <p>Inventory on hands today: {}</p>
                <p><strong>Demands today ends up to be: {}</strong></p>
                <p>Number of units sold today: {}</p>
                <p>Lost sales in units today: {}</p>
                <p>Revenue today: ${:.2f}</p>
                <p>Cost today: ${:.2f}</p>
                <p>Profit Calculation: ${:.2f} * Min(Quantity, Customer Demand) - ${:.2f} * (Quantity)</p>
                <p>Profit today: ${:.2f}</p>
                <p>Total profit: ${:.2f}</p>
                <br />
                <h4>Reminder: you will be automatically redirected to next page in 1 minute - redirect now by click the button below</h4>
                <form id="daycontinueform" name="daycontinueform" action="/pacewaiting" method="get">
                <p><button type="submit" style="width:120px;height:40px;">Continue</button></p>
                </form>
                <script type="text/javascript">
                {jsfunction}
                </script>
                '''.format(norder, ndemand, nsold, nlost, rev, cost, current_par.retail_price,
                           current_par.wholesale_price, profit, total_profit,
                           jsfunction="window.onload=function(){window.setTimeout('document.daycontinueform.submit()', 60000)}")
    return html_template(html_h1, html_body)


# waiting page after making decision (run) for paced game
# wait for all users to make a decision at this page and proceed to stats with ranking all together
@app.route('/pacewaiting', methods=['GET', 'POST'])
@login_required
def pace_waiting():
    # protect from instructors accessing this page
    if current_user.id in [10000001100, 10000002200, 10000003300]:
        return redirect('/admin')
    # extract info
    day_index = len(Game.query.filter_by(id=current_user.id).all()) + 1
    current_par = Parameter.query.filter_by(scode=current_user.scode).all()[-1]
    # users for unpaced sessions are not allowed
    if not current_par.consistent_pace:
        return redirect('/stats')
    # users for paced sessions are allowed but returns depend on conditions
    try:
        # instructor not yet opened the paced session if exception raised
        current_pace = Pace.query.filter_by(scode=current_user.scode).all()[-1]
        # id in collection 
        if current_user.id in [int(x) for x in current_pace.session_id_collection.split(',')]:
            pass
        else:  # id not in collection
            return redirect('/paceloading')
    except:
        return redirect('/paceloading')
    # pace control
    if day_index - 1 != min([len(Game.query.filter_by(id=y).all()) for y in
                             [int(x) for x in current_pace.session_id_collection.split(',')]]):
        html_h1_1 = 'Waiting for others to confirm their orders...'
        html_body_1 = ''
        return html_ar_template(html_h1_1, html_body_1, 5)
    else:
        html_h1_2 = 'All orders are confirmed!'
        html_body_2 = '''
                       <br />
                       <h4>Reminder: you will be automatically redirected to next page in 5 seconds - redirect now by click the button below</h4>
                       <form id="waitendform" name="waitendform" action="/pacestats" method="get">
                       <p><button type="submit" style="width:120px;height:40px;">Show Results</button></p> <form/>
                       <script type="text/javascript">
                       {jsfunction}
                       </script>
                       '''.format(
            jsfunction="window.onload=function(){window.setTimeout('document.waitendform.submit()', 5000)}")
        return html_ar_template(html_h1_2, html_body_2, 5)


# show paced game stats page
# show overall stats with rank (table & plot) of the game at the end of each day
@app.route('/pacestats', methods=['GET', 'POST'])
@login_required
def pace_show_stats():
    # protect from instructors accessing this page
    if current_user.id in [10000001100, 10000002200, 10000003300]:
        return redirect('/admin')
    # extract info
    day_index = len(Game.query.filter_by(id=current_user.id).all())
    current_par = Parameter.query.filter_by(scode=current_user.scode).all()[-1]
    # users for unpaced sessions are not allowed
    if not current_par.consistent_pace:
        return redirect('/stats')
    # users for paced sessions are allowed but returns depend on conditions
    try:
        # instructor not yet opened the paced session if exception raised
        current_pace = Pace.query.filter_by(scode=current_user.scode).all()[-1]
        # id in collection 
        if current_user.id in [int(x) for x in current_pace.session_id_collection.split(',')]:
            pass
        else:  # id not in collection
            return redirect('/paceloading')
    except:
        return redirect('/paceloading')
    # pace control
    if day_index != min([len(Game.query.filter_by(id=y).all()) for y in
                         [int(x) for x in current_pace.session_id_collection.split(',')]]):
        return redirect('/pacewaiting')
    # protect from new user visiting this page before make any decision
    if day_index == 0:
        return redirect(url_for('pace_day_start'))

    # update round rank
    if Game.query.filter_by(id=current_user.id, day_index=day_index).all()[-1].round_rank == 0:
        Game.query.filter_by(id=current_user.id, day_index=day_index).all()[-1].round_rank = sorted([x[0] for x in
                                                                                                     Game.query.with_entities(
                                                                                                         Game.profit).filter_by(
                                                                                                         scode=current_user.scode,
                                                                                                         day_index=day_index).all()],
                                                                                                    reverse=True).index(
            Game.query.filter_by(id=current_user.id, day_index=day_index).all()[-1].profit) + 1
        db.session.commit()
    # update total rank
    if Game.query.filter_by(id=current_user.id, day_index=day_index).all()[-1].total_rank == 0:
        Game.query.filter_by(id=current_user.id, day_index=day_index).all()[-1].total_rank = sorted([x[0] for x in
                                                                                                     Game.query.with_entities(
                                                                                                         Game.total_profit).filter_by(
                                                                                                         scode=current_user.scode,
                                                                                                         day_index=day_index).all()],
                                                                                                    reverse=True).index(
            Game.query.filter_by(id=current_user.id, day_index=day_index).all()[-1].total_profit) + 1
        db.session.commit()

    # db to df
    db_connect = sqlite3.connect('newsvendor_db.db')
    resdf = pd.read_sql_query('''SELECT day_index,norder,ndemand,nsold,nlost,profit,total_profit,round_rank,total_rank
                                 FROM game
                                 WHERE id = {}'''.format(current_user.id), db_connect)
    resdf = resdf.rename(
        columns={'day_index': 'Day #', 'norder': 'Order Placed', 'ndemand': 'Customer Demand', 'nsold': 'Sold',
                 'nlost': 'Lost Sales', 'profit': 'Profit', 'total_profit': 'Total Profit',
                 'round_rank': 'Round Rank', 'total_rank': 'Total Rank'})

    # df to plot
    resdf_for_plot = resdf.iloc[:, 0:-2]
    # conduct in function show_plot_stats_html(resdf_for_plot)

    # flask template
    html_h1 = 'Accumulated Game Stats at The End of Day {}'.format(day_index)
    html_body_end = '''
                {}
                <br />
                {}
                <br />
                <form action="/paceend" method="get">
                <p><button type="submit" style="width:120px;height:40px;">End of Game</button></p>
                </form>
                '''.format(resdf.to_html(index=False), show_plot_stats_html(resdf_for_plot, day_index))
    html_body_run = '''
                {}
                <br />
                {}
                <br />
                <h4>Reminder: you will be automatically redirected to next page in 1 minute - redirect now by click the button below</h4>
                <form id="statscontinueform" name="statscontinueform" action="/pacerun" method="get">
                <p><button type="submit" style="width:120px;height:40px;">Continue to Day {} Now</button></p>
                </form>
                <script type="text/javascript">
                {jsfunction}
                </script>
                '''.format(resdf.to_html(index=False), show_plot_stats_html(resdf_for_plot, day_index), day_index + 1,
                           jsfunction="window.onload=function(){window.setTimeout('document.statscontinueform.submit()', 60000)}")
    if day_index == current_par.nrounds:
        return html_template(html_h1, html_body_end)
    else:  # day_index < current_par.nrounds
        return html_template(html_h1, html_body_run)

    # show paced game conclusion page


# ask if user want to go back to stats and check results
@app.route('/paceend', methods=['GET', 'POST'])
@login_required
def pace_game_end():
    # protect from instructors accessing this page
    if current_user.id in [10000001100, 10000002200, 10000003300]:
        return redirect('/admin')
    # extract info
    day_index = len(Game.query.filter_by(id=current_user.id).all())
    current_par = Parameter.query.filter_by(scode=current_user.scode).all()[-1]
    # users for unpaced sessions are not allowed
    if not current_par.consistent_pace:
        return redirect('/stats')
    # users for paced sessions are allowed but returns depend on conditions
    try:
        # instructor not yet opened the paced session if exception raised
        current_pace = Pace.query.filter_by(scode=current_user.scode).all()[-1]
        # id in collection 
        if current_user.id in [int(x) for x in current_pace.session_id_collection.split(',')]:
            pass
        else:  # id not in collection
            return redirect('/paceloading')
    except:
        return redirect('/paceloading')
    # pace control
    if day_index != min([len(Game.query.filter_by(id=y).all()) for y in
                         [int(x) for x in current_pace.session_id_collection.split(',')]]):
        return redirect('/pacewaiting')
    # protect from users accessing this page until they are done (day_index = nrounds)
    if day_index < current_par.nrounds:
        return redirect(url_for('pace_show_stats'))

    # flask template
    html_h1 = 'Well done, {}! Thanks for playing!'.format(current_user.pname)
    html_body = '''
                <br />
                <form action="/pacestats" method="get">
                <p><button type="submit" style="width:120px;height:40px;">Back to Stats</button></p> <form/>
                '''
    return html_template(html_h1, html_body)


########################################################################################################################

# execution
if __name__ == '__main__':
    app.run(debug=True)
