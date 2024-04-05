# Brody Banner, Matthew Rinaldi

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from datetime import datetime
import calendar
from dotenv import load_dotenv
import os

load_dotenv()
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///calendar.db'
app.config['SECRET_KEY'] = 'bruhevent!'
db = SQLAlchemy(app)
bootstrap = Bootstrap(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

assignments_schedules = db.Table('assignments_schedules',
    db.Column('assignment_id', db.Integer, db.ForeignKey('assignment.id'), primary_key=True),
    db.Column('schedule_id', db.Integer, db.ForeignKey('schedule.id'), primary_key=True)
)

class Student(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), nullable=False)
    password = db.Column(db.String(40), nullable=False)
    assignments = db.relationship('Assignment', backref='student', lazy=True)
    schedules = db.relationship('Schedule', backref='student', lazy=True)

    def __repr__(self):
        return '<Student %r>' % self.id

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(40), nullable=False)
    due = db.Column(db.DateTime, nullable=False)
    desc = db.Column(db.String(200), nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    
    def __repr__(self):
        return '<Assignment %r>' % self.id

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(40), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    desc = db.Column(db.String(200), nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    assignments = db.relationship('Assignment', secondary=assignments_schedules, backref=db.backref('schedules', lazy=True))

    def __repr__(self):
        return '<Schedule %r>' % self.id
    
@login_manager.user_loader
def load_user(user_id):
    return Student.query.get(int(user_id))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        existing_user = Student.query.filter_by(name=name).first()
        if existing_user:
            flash('User already exists. Please log in.')
            return redirect(url_for('login'))
        new_user = Student(name=name, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('You have successfully signed up! Please log in.')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        user = Student.query.filter_by(name=name).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('year'))
        else:
            flash('Invalid username or password. Please try again.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/month/<int:month>')
@login_required
def month(month):
    month_name = calendar.month_name[month]
    start_day = calendar.monthrange(2024, month)[0] + 1
    num_days = calendar.monthrange(2024, month)[1]
    return render_template('month.html', month_name=month_name, num_days=num_days, month=month, start_day=start_day)

@app.route('/day/<int:month>/<int:day>')
@login_required
def day(month, day):
    month_name = calendar.month_name[month]
    start_day = calendar.monthrange(2024, month)[0] + 1
    day_name = calendar.day_name[((day + start_day) % 7) - 2]
    return render_template('day.html', month_name=month_name, day_name=day_name, day=day)

@app.route('/year')
@login_required
def year():
    months = {i: calendar.month_name[i] for i in range(1, 13)}
    return render_template('year.html', months=months)

def create_db():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    create_db()
    app.run(debug=True)