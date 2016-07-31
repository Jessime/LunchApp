# -*- coding: utf-8 -*-
"""
Created on Wed May 18 17:22:57 2016

@author: jessime

TODO
----
1. On new_group, require two restaurants.
"""
from flask import Flask
from flask import render_template
from flask import request
from flask import session
from flask import redirect
from flask import jsonify
from flask import flash

from flask.ext.bcrypt import Bcrypt

import os
import dropbox
import pandas as pd
import numpy as np

from traceback import format_exc
from datetime import timedelta, datetime
from random import choice
from io import StringIO
from string import ascii_letters

##############################################################################
# Data handling class
##############################################################################

class Data():
    DBX = dropbox.Dropbox('zGUHUOeJg4EAAAAAAAAz4CCY7cC7aryG9U0rWQIuLirW-iNQ5ZTzEnDG6RhIDz4n')
    OVERWRITE = dropbox.files.WriteMode('overwrite')
    
    @classmethod
    def path(self, group, user):
        return '/{}/{}.txt'.format(group, user)
    
    @classmethod    
    def listdir(self, group):
        entries = self.DBX.files_list_folder('/'+group).entries
        files = [e.name for e in entries]
        return files

    @classmethod
    def read_groups(self):
        content = self.DBX.files_download('/groups.csv')[1].content
        groups = pd.read_csv(StringIO(content.decode('utf-8')), index_col=0)
        return groups

    @classmethod        
    def write_groups(self, groups):
        temp = ''.join(choice(ascii_letters) for i in range(20))
        groups.to_csv(temp)
        self.DBX.files_upload(open(temp), '/groups.csv', mode=self.OVERWRITE)

    @classmethod        
    def make_group(self, new):
        self.DBX.files_create_folder(new)
        
    @classmethod
    def add_user(self, group, user):
        users = [u[:-4] for u in self.listdir(group)]
        print(users)
        new = self.path(group, user)
        if user in users:
            pass
        elif users:
            rand_file = self.path(group, choice(users))
            print(rand_file)
            print(new)
            self.DBX.files_copy(rand_file, new)
        else:
            series = pd.Series(index=['here'], data=[0])
            self.write(group, user, series)

    @classmethod            
    def read_full(self, group):
        users = [u[:-4] for u in self.listdir(group)]
        series = []
        for u in users:
            series.append(self.read(group, u))
        return pd.DataFrame(data=series, index=users)

    @classmethod        
    def write_full(self, group, df):
        for series in df.iterrows():
            self.write(group, series[0], series[1])
            
    @classmethod
    def read(self, group, user):
        content = self.DBX.files_download(self.path(group, user))[1].content
        series = pd.Series.from_csv(StringIO(content.decode('utf-8')), index_col=0)
        return series
        
    @classmethod
    def write(self, group, user, series):
        temp = ''.join(choice(ascii_letters) for i in range(20))
        series.to_csv(temp)
        self.DBX.files_upload(open(temp), 
                              self.path(group, user), 
                              mode=self.OVERWRITE)
                              
    @classmethod
    def log_error(self, group, user, error):
        time = datetime.strftime(datetime.now(), '%Y.%m.%d %H.%M.%S')
        content = "Group: {} \n User: {} \n\n\n {}".format(group, user, error)
        with open(time, 'w') as error_file:
            error_file.write(content)
        self.DBX.files_upload(open(time), '/errors/{}.txt'.format(time))
        
##############################################################################
##############################################################################

app = Flask(__name__)
app.secret_key = 'this key should be complex'
bcrypt = Bcrypt(app)

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(days=365)
    
@app.route('/current_weights', methods=['GET', 'POST'])
def current_weights():
    if request.method == 'POST':
        series = pd.read_json(request.form['restaurants_field'], typ='series')
        series.ix['here'] = 1 
        Data.write(session['group'], session['username'], series)
        return redirect('/')
        
    restaurants = Data.read(session['group'], session['username'])
    restaurants = restaurants.drop('here')
    return render_template('current_weights.html',
                           group=session['group'],
                           name=session['username'],
                           restaurants=restaurants.to_dict())

@app.route('/reset')
def reset():
    
    groups = Data.read_groups()
    date = datetime.strftime(datetime.now(), '%m/%d')
    groups.set_value(session['group'], 'reset_date', date)
    Data.write_groups(groups)
    
    data = Data.read_full(session['group'])
    data.here.replace(1, 0, inplace=True)
    Data.write_full(session['group'], data)
    return jsonify(result=True)
    
@app.route('/more')
def more():
    return render_template('more.html',
                           name=session['username'],
                           group=session['group'])
    
@app.route('/add_restaurant', methods=['GET', 'POST'])
def add_restaurant():
    if request.method == 'POST':
        data = Data.read_full(session['group'])
        rest = request.form['restaurant']
        if rest not in data:
            data[rest] = [0]*data.shape[0]
            Data.write_full(session['group'], data)
        return redirect('/')
            
    return render_template('add_restaurant.html')

@app.route('/del_restaurant', methods=['GET', 'POST'])
def del_restaurant():
    if request.method == 'POST':
        data = Data.read_full(session['group'])
        rest = request.form['restaurant']
        if rest in data:
            data.drop(rest, axis=1, inplace=True)
            Data.write_full(session['group'], data)
        return redirect('/')
            
    return render_template('del_restaurant.html')
    
@app.route('/table')
def table():
    data = Data.read_full(session['group'])
    data.ix['CHECKED'] = data[data.here == 1].sum()
    data = data.drop('here', 1)
    
    checked_sum = data.ix['CHECKED'].sum()
    if checked_sum > 0:
        percent = 100 * data.ix['CHECKED'] / checked_sum
        data.ix['PERCENT'] = np.array(percent, dtype=np.int64)

    data = data.transpose()
    cols = data.columns.tolist()
    cols = cols[-2:] + cols[:-2]
    data = data[cols]
    data = data.sort_values('CHECKED', ascending=False)
    return render_template('table.html', 
                           table=data.to_html(classes='female'),
                           group=session['group'])
    
@app.route('/help_page')
def help_page():
    return render_template('help_page.html', 
                           name=session['username'],
                           group=session['group'])    
    
@app.route('/check_in')
def check_in():
    series = Data.read(session['group'], session['username'])
    series.here = 1
    Data.write(session['group'], session['username'], series)
    return jsonify(result=True)
    
@app.route('/pick_lunch')
def pick_lunch():
    data = Data.read_full(session['group'])
    filtered_data = data[data.here == 1]
    filtered_data = filtered_data.drop('here', 1)
    
    restaurant_points = filtered_data.sum(0)
    if True: #TODO : Make this optional
        restaurant_points = restaurant_points.nlargest(3)
    restaurant_norm = restaurant_points / restaurant_points.sum()
    try:
        result = restaurant_norm.sample(weights=restaurant_norm).index[0]
        result = 'You should go to {}!'.format(result)
    except ValueError:
        result = 'Nobody has checked in yet.'
    return jsonify(result=result)

##############################################################################
# Account Setup Functions
##############################################################################
@app.route('/new_or_join_group')
def new_or_join_group():
    return render_template('new_or_join_group.html', name=session['username'])

@app.route('/new_group', methods=['GET', 'POST'])
def new_group():
    if request.method == 'POST':
        groups = Data.read_groups()
        new = request.form['group']
        if new not in groups.index:
            hash_pw = bcrypt.generate_password_hash(request.form['password'])
            groups.loc[new] = [hash_pw]
            Data.write_groups(groups)
            Data.make_group(new)
            session['group'] = new
            Data.add_user(new, session['username'])
            return redirect('/')
        else: 
            flash('This group already exists. Please choose a new name.')
            redirect('new_group')
    return render_template('new_group.html', name=session['username'])

@app.route('/join_group', methods=['GET', 'POST'])
def join_group():
    if request.method == 'POST':
        all_groups = Data.read_groups()
        join = request.form['group']
        submit_pw = request.form['password']
        
        if join in all_groups.index:

            hash_pw = all_groups.ix[join]['password']
            correct = bcrypt.check_password_hash(hash_pw, submit_pw)
            if correct:
                session['group'] = join
                Data.add_user(join, session['username'])
                return redirect('/')
        else:
            flash('That was not an existing group. Try again or make a new group.')
            return redirect('new_or_join_group')
            
    return render_template('join_group.html', name=session['username'])
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    make_session_permanent()
    if request.method == 'POST':
        session['username'] = request.form['username']
        session['password'] = request.form['password']
        
        return redirect('/new_or_join_group')
    
    return render_template('login.html')

##############################################################################
##############################################################################

@app.route('/', methods=['GET', 'POST'])    
def index():
    try:      
        if ('username' in session) and ('group' in session):
            groups = Data.read_groups()
            reset_date = groups['reset_date'][session['group']]
            here = Data.read(session['group'], session['username'])['here']
            return render_template('index.html', 
                                   name=session['username'], 
                                   group=session['group'],
                                   here=here,
                                   reset_date=reset_date)
        else:
            return redirect('login')
    except Exception:
        error = format_exc()
        Data.log_error(session['group'], session['username'], error)

if __name__ == '__main__':
    app.debug = False
    port = int(os.environ.get('PORT',5000))
    app.run(host='0.0.0.0', port=port)