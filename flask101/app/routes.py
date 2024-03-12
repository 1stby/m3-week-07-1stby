from datetime import datetime, timezone
from urllib.parse import urlsplit
from flask import render_template, flash, redirect, url_for, request, session
from flask_login import login_user, logout_user, current_user, login_required
from flask_wtf.csrf import generate_csrf
import sqlalchemy as sa
from app import app, db
from app.forms import LoginForm,RegistrationForm, EditProfileForm
from app.models import User
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import text

@app.route('/')
@app.route('/index')
@login_required
def index():
    user = {'username': 'Toby'}
    posts = [
        {
            'author': {'username': 'John'},
            'body': 'Portland 的天氣真好！'
        },
        {
            'author': {'username': 'Susan'},
            'body': '復仇者聯盟電影真的很酷！'
        }
    ]
    return render_template('index.html', title='首頁',  posts=posts)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password2 = request.form['password2']
        #檢查是否已有相同的username
        sql_query = text("SELECT * FROM User WHERE username = :username or email = :email")
        result = db.session.execute(sql_query, {'username':username, 'email':email})
        check_user = result.fetchone()
        if check_user:
            flash('使用者以存在')
            return redirect(url_for('register'))
        if password != password2:
            flash('密碼不一樣')
            return redirect(url_for('register'))

        sql_insert = text("INSERT INTO User (username, email, password_hash) VALUES(:username, :email, :password_hash)")
        db.session.execute(sql_insert, {'username':username, 'email':email, 'password_hash':generate_password_hash(password)})
        db.session.commit()
    flash('註冊成功')    
    return render_template('register.html', title = 'Register', csrf_token=generate_csrf)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        sql_query = text("SELECT * FROM User WHERE username = :username")
        result = db.session.execute(sql_query, {'username':username})
        user = result.fetchone()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('index'))
        else:
            flash('密碼錯誤')
            return redirect(url_for('login'))

    return render_template('login.html', title='Log in', csrf_token=generate_csrf)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))



@app.route('/user/<username>')
@login_required
def user(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    posts = [
        {'author': user, 'body': '今天天氣真好 '},
        {'author': user, 'body': '好想吃火鍋 '}
    ]
    return render_template('user.html', user=user, posts=posts)

@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile',form=form)
