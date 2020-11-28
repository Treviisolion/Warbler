import os
from unittest import TestCase
from flask import url_for
from models import db, Message, User, Likes, Follows, datetime

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.drop_all()
db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False

# Prevents any redirects from happening even if tests are run in development mode
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

# In case autocorrect changes order of imporation
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///warbler-test'

# Base domain for testing. Change if testing environment is different
DOMAIN = "http://localhost"

# Test image for image testing
TEST_IMAGE = 'https://homepages.cae.wisc.edu/~ece533/images/airplane.png'


class UserModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.app_context = app.test_request_context()
        self.app_context.push()
        self.client = app.test_client()

        self.testuser = User.signup(
            username="testuser", email="test@test.com", password="testuser", image_url=None)
        self.testuser_2 = User.signup(
            username="testinguser", email="testing@testing.com", password="testinguser", image_url=TEST_IMAGE)
        self.testuser_3 = User.signup(
            username="testusers", email="user@testing.com", password="testusers", image_url=None)
        self.testuser_4 = User.signup(
            username="testingusers", email="users@testing.com", password="tests", image_url=None)
        db.session.commit()

        self.testmsg = Message(
            text="Testing", user_id=self.testuser.id)
        self.testmsg_2 = Message(
            text="More testing", user_id=self.testuser.id)
        self.testmsg_3 = Message(
            text="And testing", user_id=self.testuser_2.id)
        self.testmsg_4 = Message(
            text="Yet more testing", user_id=self.testuser_2.id)
        self.testmsg_5 = Message(
            text="Any more testing?", user_id=self.testuser_3.id)
        self.testmsg_6 = Message(
            text="Last one I think", user_id=self.testuser_3.id)
        db.session.add(self.testmsg)
        db.session.add(self.testmsg_2)
        db.session.add(self.testmsg_3)
        db.session.add(self.testmsg_4)
        db.session.add(self.testmsg_5)
        db.session.add(self.testmsg_6)
        db.session.commit()

        like = Likes(user_id=self.testuser_2.id, message_id=self.testmsg_2.id)
        like2 = Likes(user_id=self.testuser.id, message_id=self.testmsg_4.id)
        like3 = Likes(user_id=self.testuser.id, message_id=self.testmsg_6.id)
        follow = Follows(user_being_followed_id=self.testuser_2.id,
                         user_following_id=self.testuser.id)
        follow2 = Follows(user_being_followed_id=self.testuser_3.id,
                          user_following_id=self.testuser_4.id)
        follow3 = Follows(user_being_followed_id=self.testuser_4.id,
                          user_following_id=self.testuser_3.id)
        db.session.add(like)
        db.session.add(like2)
        db.session.add(like3)
        db.session.add(follow)
        db.session.add(follow2)
        db.session.add(follow3)
        db.session.commit()

    def tearDown(self):
        """Clear any fouled transactions"""
        db.session.rollback()

    def test_list_user_non_user(self):
        """Users show up for non users?"""

        with self.client as c:
            resp = c.get(url_for('list_users'))
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn('<div class="alert', html)
            self.assertIn(f'<img src="{self.testuser.header_image_url}" alt=""', html)
            self.assertIn(f'<img src="{self.testuser_2.header_image_url}" alt=""', html)
            self.assertIn(f'<img src="{self.testuser_3.header_image_url}" alt=""', html)
            self.assertIn(f'<img src="{self.testuser_4.header_image_url}" alt=""', html)
            self.assertIn(f'<a href="/users/{self.testuser.id}"', html)
            self.assertIn(f'<a href="/users/{self.testuser_2.id}"', html)
            self.assertIn(f'<a href="/users/{self.testuser_3.id}"', html)
            self.assertIn(f'<a href="/users/{self.testuser_4.id}"', html)
            self.assertIn(f'<img src="{self.testuser.image_url}" alt="{self.testuser.username} Image"', html)
            self.assertIn(f'<img src="{self.testuser_2.image_url}" alt="{self.testuser_2.username} Image"', html)
            self.assertIn(f'<img src="{self.testuser_3.image_url}" alt="{self.testuser_3.username} Image"', html)
            self.assertIn(f'<img src="{self.testuser_4.image_url}" alt="{self.testuser_4.username} Image"', html)
            self.assertIn(f'<p>@{self.testuser.username}</p>', html)
            self.assertIn(f'<p>@{self.testuser_2.username}</p>', html)
            self.assertIn(f'<p>@{self.testuser_3.username}</p>', html)
            self.assertIn(f'<p>@{self.testuser_4.username}</p>', html)
            self.assertNotIn('<form method="POST"', html)
            self.assertIn(f'<p class="card-bio">{self.testuser.bio}</p>', html)
            self.assertIn(f'<p class="card-bio">{self.testuser_2.bio}</p>', html)
            self.assertIn(f'<p class="card-bio">{self.testuser_3.bio}</p>', html)
            self.assertIn(f'<p class="card-bio">{self.testuser_4.bio}</p>', html)

    def test_list_user_as_user(self):
        """Users show up for users?"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id
            
            resp = c.get(url_for('list_users'))
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn('<div class="alert', html)
            self.assertIn(f'<img src="{self.testuser.header_image_url}" alt=""', html)
            self.assertIn(f'<img src="{self.testuser_2.header_image_url}" alt=""', html)
            self.assertIn(f'<img src="{self.testuser_3.header_image_url}" alt=""', html)
            self.assertIn(f'<img src="{self.testuser_4.header_image_url}" alt=""', html)
            self.assertIn(f'<a href="/users/{self.testuser.id}"', html)
            self.assertIn(f'<a href="/users/{self.testuser_2.id}"', html)
            self.assertIn(f'<a href="/users/{self.testuser_3.id}"', html)
            self.assertIn(f'<a href="/users/{self.testuser_4.id}"', html)
            self.assertIn(f'<img src="{self.testuser.image_url}" alt="{self.testuser.username} Image"', html)
            self.assertIn(f'<img src="{self.testuser_2.image_url}" alt="{self.testuser_2.username} Image"', html)
            self.assertIn(f'<img src="{self.testuser_3.image_url}" alt="{self.testuser_3.username} Image"', html)
            self.assertIn(f'<img src="{self.testuser_4.image_url}" alt="{self.testuser_4.username} Image"', html)
            self.assertIn(f'<p>@{self.testuser.username}</p>', html)
            self.assertIn(f'<p>@{self.testuser_2.username}</p>', html)
            self.assertIn(f'<p>@{self.testuser_3.username}</p>', html)
            self.assertIn(f'<p>@{self.testuser_4.username}</p>', html)
            self.assertNotIn(f'<form method="POST" action="/users/stop-following/{self.testuser.id}"', html)
            self.assertIn(f'<form method="POST" action="/users/stop-following/{self.testuser_2.id}"', html)
            self.assertNotIn(f'<form method="POST" action="/users/stop-following/{self.testuser_3.id}"', html)
            self.assertNotIn(f'<form method="POST" action="/users/stop-following/{self.testuser_4.id}"', html)
            self.assertNotIn(f'<form method="POST" action="/users/follow/{self.testuser.id}"', html)
            self.assertNotIn(f'<form method="POST" action="/users/follow/{self.testuser_2.id}"', html)
            self.assertIn(f'<form method="POST" action="/users/follow/{self.testuser_3.id}"', html)
            self.assertIn(f'<form method="POST" action="/users/follow/{self.testuser_4.id}"', html)
            self.assertIn(f'<p class="card-bio">{self.testuser.bio}</p>', html)
            self.assertIn(f'<p class="card-bio">{self.testuser_2.bio}</p>', html)
            self.assertIn(f'<p class="card-bio">{self.testuser_3.bio}</p>', html)
            self.assertIn(f'<p class="card-bio">{self.testuser_4.bio}</p>', html)

    def test_show_user_non_user(self):
        """User shows up for non users?"""

        with self.client as c:
            resp = c.get(url_for('users_show', user_id=self.testuser.id))
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn('<div class="alert', html)
            self.assertIn(f'style="background-image: url({self.testuser.header_image_url});"', html)
            self.assertIn(f'<img src="{self.testuser.image_url}" alt="{self.testuser.username} image"', html)
            self.assertIn(f'<a href="/users/{self.testuser.id}">{len(self.testuser.messages)}</a>', html)
            self.assertIn(f'<a href="/users/{self.testuser.id}/following">{len(self.testuser.following)}</a>', html)
            self.assertIn(f'<a href="/users/{self.testuser.id}/followers">{len(self.testuser.followers)}</a>', html)
            self.assertIn(f'<a href="/users/{self.testuser.id}/likes">{len(self.testuser.likes)}</a>', html)
            self.assertNotIn(f'<a href="/users/profile"', html)
            self.assertNotIn(f'<form method="POST" action="/users/delete"', html)
            self.assertNotIn(f'<form method="POST" action="/users/stop-following/{self.testuser.id}"', html)
            self.assertNotIn(f'<form method="POST" action="/users/follow/{self.testuser.id}"', html)
            self.assertIn(f'<a href="/messages/{self.testmsg.id}"', html)
            self.assertIn(f'<a href="/messages/{self.testmsg_2.id}"', html)
            self.assertIn(f'<a href="/users/{self.testuser.id}"', html)
            self.assertIn(f'<img src="{self.testuser.image_url}" alt="{self.testuser.username} image"', html)
            self.assertIn(f'<a href="/users/{self.testuser.id}">@{self.testuser.username}</a>', html)
            self.assertIn(f'<span class="text-muted">{self.testmsg.timestamp.strftime("%d %B %Y")}</span>', html)
            self.assertIn(f'<span class="text-muted">{self.testmsg_2.timestamp.strftime("%d %B %Y")}</span>', html)
            self.assertIn(f'<p>{self.testmsg.text}</p>', html)
            self.assertIn(f'<p>{self.testmsg_2.text}</p>', html)
            self.assertNotIn(f'<form method="POST" action="/users/remove_like/{self.testmsg.id}"', html)
            self.assertNotIn(f'<form method="POST" action="/users/remove_like/{self.testmsg_2.id}"', html)
            self.assertNotIn(f'<form method="POST" action="/users/add_like/{self.testmsg.id}"', html)
            self.assertNotIn(f'<form method="POST" action="/users/add_like/{self.testmsg_2.id}"', html)

    def test_show_user_own_user(self):
        """User shows up for self?"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.get(url_for('users_show', user_id=self.testuser.id))
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn('<div class="alert', html)
            self.assertIn(f'style="background-image: url({self.testuser.header_image_url});"', html)
            self.assertIn(f'<img src="{self.testuser.image_url}" alt="{self.testuser.username} image"', html)
            self.assertIn(f'<a href="/users/{self.testuser.id}">{len(self.testuser.messages)}</a>', html)
            self.assertIn(f'<a href="/users/{self.testuser.id}/following">{len(self.testuser.following)}</a>', html)
            self.assertIn(f'<a href="/users/{self.testuser.id}/followers">{len(self.testuser.followers)}</a>', html)
            self.assertIn(f'<a href="/users/{self.testuser.id}/likes">{len(self.testuser.likes)}</a>', html)
            self.assertIn(f'<a href="/users/profile"', html)
            self.assertIn(f'<form method="POST" action="/users/delete"', html)
            self.assertNotIn(f'<form method="POST" action="/users/stop-following/{self.testuser.id}"', html)
            self.assertNotIn(f'<form method="POST" action="/users/follow/{self.testuser.id}"', html)
            self.assertIn(f'<a href="/messages/{self.testmsg.id}"', html)
            self.assertIn(f'<a href="/messages/{self.testmsg_2.id}"', html)
            self.assertIn(f'<a href="/users/{self.testuser.id}"', html)
            self.assertIn(f'<img src="{self.testuser.image_url}" alt="{self.testuser.username} image"', html)
            self.assertIn(f'<a href="/users/{self.testuser.id}">@{self.testuser.username}</a>', html)
            self.assertIn(f'<span class="text-muted">{self.testmsg.timestamp.strftime("%d %B %Y")}</span>', html)
            self.assertIn(f'<span class="text-muted">{self.testmsg_2.timestamp.strftime("%d %B %Y")}</span>', html)
            self.assertIn(f'<p>{self.testmsg.text}</p>', html)
            self.assertIn(f'<p>{self.testmsg_2.text}</p>', html)
            self.assertNotIn(f'<form method="POST" action="/users/remove_like/{self.testmsg.id}"', html)
            self.assertNotIn(f'<form method="POST" action="/users/remove_like/{self.testmsg_2.id}"', html)
            self.assertNotIn(f'<form method="POST" action="/users/add_like/{self.testmsg.id}"', html)
            self.assertNotIn(f'<form method="POST" action="/users/add_like/{self.testmsg_2.id}"', html)

    def test_show_user_other_user_not_following(self):
        """User shows up for other users not following them?"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_2.id

            resp = c.get(url_for('users_show', user_id=self.testuser.id))
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn('<div class="alert', html)
            self.assertIn(f'style="background-image: url({self.testuser.header_image_url});"', html)
            self.assertIn(f'<img src="{self.testuser.image_url}" alt="{self.testuser.username} image"', html)
            self.assertIn(f'<a href="/users/{self.testuser.id}">{len(self.testuser.messages)}</a>', html)
            self.assertIn(f'<a href="/users/{self.testuser.id}/following">{len(self.testuser.following)}</a>', html)
            self.assertIn(f'<a href="/users/{self.testuser.id}/followers">{len(self.testuser.followers)}</a>', html)
            self.assertIn(f'<a href="/users/{self.testuser.id}/likes">{len(self.testuser.likes)}</a>', html)
            self.assertNotIn(f'<a href="/users/profile"', html)
            self.assertNotIn(f'<form method="POST" action="/users/delete"', html)
            self.assertNotIn(f'<form method="POST" action="/users/stop-following/{self.testuser.id}"', html)
            self.assertIn(f'<form method="POST" action="/users/follow/{self.testuser.id}"', html)
            self.assertIn(f'<a href="/messages/{self.testmsg.id}"', html)
            self.assertIn(f'<a href="/messages/{self.testmsg_2.id}"', html)
            self.assertIn(f'<a href="/users/{self.testuser.id}"', html)
            self.assertIn(f'<img src="{self.testuser.image_url}" alt="{self.testuser.username} image"', html)
            self.assertIn(f'<a href="/users/{self.testuser.id}">@{self.testuser.username}</a>', html)
            self.assertIn(f'<span class="text-muted">{self.testmsg.timestamp.strftime("%d %B %Y")}</span>', html)
            self.assertIn(f'<span class="text-muted">{self.testmsg_2.timestamp.strftime("%d %B %Y")}</span>', html)
            self.assertIn(f'<p>{self.testmsg.text}</p>', html)
            self.assertIn(f'<p>{self.testmsg_2.text}</p>', html)
            self.assertNotIn(f'<form method="POST" action="/users/remove_like/{self.testmsg.id}"', html)
            self.assertIn(f'<form method="POST" action="/users/remove_like/{self.testmsg_2.id}"', html)
            self.assertIn(f'<form method="POST" action="/users/add_like/{self.testmsg.id}"', html)
            self.assertNotIn(f'<form method="POST" action="/users/add_like/{self.testmsg_2.id}"', html)

    def test_show_user_other_user_following(self):
        """User shows up for other users following them?"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.get(url_for('users_show', user_id=self.testuser_2.id))
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn('<div class="alert', html)
            self.assertIn(f'style="background-image: url({self.testuser_2.header_image_url});"', html)
            self.assertIn(f'<img src="{self.testuser_2.image_url}" alt="{self.testuser_2.username} image"', html)
            self.assertIn(f'<a href="/users/{self.testuser_2.id}">{len(self.testuser_2.messages)}</a>', html)
            self.assertIn(f'<a href="/users/{self.testuser_2.id}/following">{len(self.testuser_2.following)}</a>', html)
            self.assertIn(f'<a href="/users/{self.testuser_2.id}/followers">{len(self.testuser_2.followers)}</a>', html)
            self.assertIn(f'<a href="/users/{self.testuser_2.id}/likes">{len(self.testuser_2.likes)}</a>', html)
            self.assertNotIn(f'<a href="/users/profile"', html)
            self.assertNotIn(f'<form method="POST" action="/users/delete"', html)
            self.assertIn(f'<form method="POST" action="/users/stop-following/{self.testuser_2.id}"', html)
            self.assertNotIn(f'<form method="POST" action="/users/follow/{self.testuser_2.id}"', html)
            self.assertIn(f'<a href="/messages/{self.testmsg_3.id}"', html)
            self.assertIn(f'<a href="/messages/{self.testmsg_4.id}"', html)
            self.assertIn(f'<a href="/users/{self.testuser_2.id}"', html)
            self.assertIn(f'<img src="{self.testuser_2.image_url}" alt="{self.testuser_2.username} image"', html)
            self.assertIn(f'<a href="/users/{self.testuser_2.id}">@{self.testuser_2.username}</a>', html)
            self.assertIn(f'<span class="text-muted">{self.testmsg_3.timestamp.strftime("%d %B %Y")}</span>', html)
            self.assertIn(f'<span class="text-muted">{self.testmsg_4.timestamp.strftime("%d %B %Y")}</span>', html)
            self.assertIn(f'<p>{self.testmsg_3.text}</p>', html)
            self.assertIn(f'<p>{self.testmsg_4.text}</p>', html)
            self.assertNotIn(f'<form method="POST" action="/users/remove_like/{self.testmsg_3.id}"', html)
            self.assertIn(f'<form method="POST" action="/users/remove_like/{self.testmsg_4.id}"', html)
            self.assertIn(f'<form method="POST" action="/users/add_like/{self.testmsg_3.id}"', html)
            self.assertNotIn(f'<form method="POST" action="/users/add_like/{self.testmsg_4.id}"', html)

    def test_show_user_followers_non_user(self):
        """Does a user's followers not show up for non-users"""

        with self.client as c:
            user = self.testuser
            resp = c.get(url_for('show_followers', user_id=user.id))

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, f'{DOMAIN}{url_for("homepage")}')

            resp2 = c.get(resp.location)
            html = resp2.get_data(as_text=True)

            self.assertEqual(resp2.status_code, 200)
            self.assertIn('<div class="alert alert-danger">Access unauthorized.</div>', html)
