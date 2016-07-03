# -*- coding: utf-8 -*-
"""
Created on Wed May 18 17:22:57 2016

@author: jessime

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

from datetime import timedelta
from random import choice
from shutil import copyfile
from io import StringIO
from string import ascii_letters

##############################################################################
# Data handling functions
##############################################################################

dbx = dropbox.Dropbox('zGUHUOeJg4EAAAAAAAAz4CCY7cC7aryG9U0rWQIuLirW-iNQ5ZTzEnDG6RhIDz4n')

def read_groups():
    global dbx
    content = dbx.files_download('/groups.csv')[1].content
    groups = pd.read_csv(StringIO(content.decode('utf-8')), index_col=0)
    return groups
    
def write_groups(groups):
    global dbx
    temp = ''.join(choice(ascii_letters) for i in range(20))
    groups.to_csv(temp)
    dbx.files_upload(open(temp), '/groups.csv', mode=dropbox.files.WriteMode('overwrite'))
    
def make_group(new):
    global dbx
    dbx.files_create_folder('/{}'.format(new))

def add_user(group, user):
    files = os.listdir('data/{}/default/'.format(group))
    if user in files:
        pass
    elif files:
        rand_file = 'data/{}/default/{}'.format(group, choice(files))
        copyfile(rand_file, 'data/{}/default/{}'.format(group, user))
        copyfile(rand_file, 'data/{}/current/{}'.format(group, user))        
    else:
        series = pd.Series(index=['here'], data=[0])
        series.to_csv('data/{}/default/{}'.format(group, user))
        series.to_csv('data/{}/current/{}'.format(group, user))
        
def read_full(group, folder='current'):
    users = os.listdir('data/{}/{}/'.format(group,folder))
    series = []
    for u in users:
        path = 'data/{}/{}/{}'.format(group, folder, u)
        series.append(pd.Series.from_csv(path))
    return pd.DataFrame(data=series, index=users)
    
def write_full(group, df, folder='current'):
    for series in df.iterrows():
        path = 'data/{}/{}/{}'.format(group, folder, series[0])
        series[1].to_csv(path)
        
def read(group, user, folder='current'):
    path = 'data/{}/{}/{}'.format(group, folder, user)
    return pd.Series.from_csv(path)
    
def write(group, user, series, folder='current'):
    path = 'data/{}/{}/{}'.format(group, folder, user)
    return series.to_csv(path)        
    
##############################################################################
##############################################################################

app = Flask(__name__)
app.secret_key = 'this key should be complex'
bcrypt = Bcrypt(app)

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(days=1)
    
@app.route('/current_weights', methods=['GET', 'POST'])
def current_weights():
    if request.method == 'POST':
        series = pd.read_json(request.form['restaurants_field'], typ='series')
        series.ix['here'] = 1 #TODO Read this from a file
        write(session['group'], session['username'], series)
        return redirect('/')
    restaurants = read(session['group'], session['username'])
    restaurants = restaurants.drop('here')
    return render_template('current_weights.html',
                           group=session['group'],
                           name=session['username'],
                           restaurants=restaurants.to_dict())

@app.route('/reset')
def reset():
    data = read_full(session['group'])
    data.here.replace(1, 0, inplace=True)
    write_full(session['group'], data)
    write_full(session['group'], data, folder='default')
    return jsonify(result=True)
    
@app.route('/more')
def more():
    return render_template('more.html',
                           name=session['username'],
                           group=session['group'])
    
@app.route('/add_restaurant', methods=['GET', 'POST'])
def add_restaurant():
    if request.method == 'POST':
        current = read_full(session['group'])
        rest = request.form['restaurant']
        if rest not in current:
            current[rest] = [0]*current.shape[0]
            write_full(session['group'], current)
            default = read_full(session['group'], 'default')
            default[rest] = [0]*default.shape[0]
            write_full(session['group'], default, 'default')
        return redirect('/')
            
    return render_template('add_restaurant.html')

@app.route('/del_restaurant', methods=['GET', 'POST'])
def del_restaurant():
    if request.method == 'POST':
        current = read_full(session['group'])
        rest = request.form['restaurant']
        if rest in current:
            current.drop(rest, axis=1, inplace=True)
            write_full(session['group'], current)
            default = read_full(session['group'], 'default')
            default.drop(rest, axis=1, inplace=True)
            write_full(session['group'], default, 'default')
        return redirect('/')
            
    return render_template('del_restaurant.html')
    
@app.route('/table')
def table():
    table = read_full(session['group'])
    table.ix['CHECKED'] = table[table.here == 1].sum()
    table = table.drop('here', 1)
    percent = 100 * table.ix['CHECKED'] / table.ix['CHECKED'].sum()
    table.ix['PERCENT'] = np.array(percent, dtype=np.int64)

    table = table.transpose()
    cols = table.columns.tolist()
    cols = cols[-2:] + cols[:-2]
    table = table[cols]
    table = table.sort_values('CHECKED', ascending=False)
    return render_template('table.html', 
                           table=table.to_html(classes='female'),
                           group=session['group'])
    
@app.route('/help_page')
def help_page():
    return render_template('help_page.html', 
                           name=session['username'],
                           group=session['group'])    
    
@app.route('/check_in')
def check_in():
    series = read(session['group'], session['username'])
    series.here = 1
    write(session['group'], session['username'], series)
    return jsonify(result=True)
    
@app.route('/pick_lunch')
def pick_lunch():
    data = read_full(session['group'])
    filtered_data = data[data.here == 1]
    filtered_data = filtered_data.drop('here', 1)
    
    restaurant_points = filtered_data.sum(0)
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
        #1/0
        groups = read_groups()
        new = request.form['group']
        if new not in groups.index:
            hash_pw = bcrypt.generate_password_hash(request.form['password'])
            groups.loc[new] = [hash_pw]
            write_groups(groups)
            make_group(new)
            session['group'] = new
            add_user(new, session['username'])
            return redirect('/')
        else: 
            flash('This group already exists. Please choose a new name.')
            redirect('new_group')
    return render_template('new_group.html', name=session['username'])

@app.route('/join_group', methods=['GET', 'POST'])
def join_group():
    if request.method == 'POST':
        all_groups = pd.read_csv('data/groups.csv', index_col=0)
        join = request.form['group']
        submit_pw = request.form['password']
        
        if join in all_groups.index:

            hash_pw = all_groups.ix[join]['password']
            correct = bcrypt.check_password_hash(hash_pw, submit_pw)
            if correct:
                session['group'] = join
                add_user(join, session['username'])
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
    if 'username' in session:
        try:
            here = read(session['group'], session['username'])['here']
            return render_template('index.html', 
                                   name=session['username'], 
                                   group=session['group'],
                                   here=here)
        except OSError:
            return redirect('login')
    else:
        return redirect('login')


if __name__ == '__main__':
    app.debug = True
    port = int(os.environ.get('PORT',5000))
    app.run(host='0.0.0.0', port=port)
    
