from datetime import datetime, timezone
from hashlib import md5
from sqlalchemy import Column, Integer, VARCHAR, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login
import sqlalchemy as sa
import sqlalchemy.orm as so


followers = db.Table(
    'followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = Column(Integer, primary_key=True)
    username = Column(VARCHAR(64), unique=True, nullable=False)
    email = Column(VARCHAR(120), unique=True, nullable=False)
    password_hash = Column(VARCHAR(256), nullable=False)
    about_me = Column(VARCHAR(140))
    last_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    posts = relationship('Post', back_populates='author')

    following = db.relationship(
        'User',secondary=followers,
        primaryjoin=(followers.c.followed_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        back_populates = 'followers')

    followers = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.followed_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        back_populates = 'following')

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'

    def follow(self, user):
        if not self.is_following(user):
            self.following.add(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.following.remove(user)

    def is_following(self, user):
        query = self.following.select().where(User.id == user.id)
        return db.session.scalar(query) is not None

    def followers_count(self):
        query = sa.select(sa.func.count()).select_from(
            self.followers.select().subquery())
        return db.session.scalar(query)

    def following_count(self):
        query = sa.select(sa.func.count()).select_from(
            self.following.select().subquery())
        return db.session.scalar(query)

    def following_posts(self):
        Author = so.aliased(User)
        Follower = so.aliased(User)
        return (
            sa.select(Post)
            .join(Post.author.of_type(Author))
            .join(Author.followers.of_type(Follower), isouter=True)
            .where(sa.or_(
                Follower.id == self.id,
                Author.id == self.id,
            ))
            .group_by(Post)
            .order_by(Post.timestamp.desc())
        )
    
@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Post(db.Model):
    id = Column(Integer, primary_key=True)
    body = Column(VARCHAR(140))
    timestamp = Column(DateTime, index=True, default=lambda: datetime.now(timezone.utc))
    user_id = Column(Integer, ForeignKey('user.id'), index=True)

    author = relationship('User', back_populates='posts')

    def __repr__(self):
        return '<Post {}>'.format(self.body)
