"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


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


class MessageViewTestCase(TestCase):
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
        db.session.commit()

        self.testmsg = Message(
            text="Testing", user_id=self.testuser.id)
        self.testmsg_2 = Message(
            text="More testing", user_id=self.testuser.id)
        self.testmsg_3 = Message(
            text="And testing", user_id=self.testuser_2.id)
        self.testmsg_4 = Message(
            text="Yet more testing", user_id=self.testuser_2.id)
        db.session.add(self.testmsg)
        db.session.add(self.testmsg_2)
        db.session.add(self.testmsg_3)
        db.session.add(self.testmsg_4)
        db.session.commit()

        like = Likes(user_id=self.testuser_2.id, message_id=self.testmsg_2.id)
        like2 = Likes(user_id=self.testuser.id, message_id=self.testmsg_4.id)
        follow = Follows(user_being_followed_id=self.testuser_2.id,
                         user_following_id=self.testuser.id)
        db.session.add(like)
        db.session.add(like2)
        db.session.add(follow)
        db.session.commit()

    def tearDown(self):
        """Clear any fouled transactions"""
        db.session.rollback()

    def test_add_message_form(self):
        """Does form for adding message appear properly"""

        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            resp = c.get(url_for('messages_add'))
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn('<div class="alert', html)
            self.assertIn("<textarea", html)
            self.assertIn("<button", html)
            self.assertNotIn('<span class="danger">', html)

    def test_add_message(self):
        """Can use add a message?"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            cur_date = datetime.utcnow()
            resp = c.post(url_for('messages_add'), data={"text": "Hello"})

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(
                resp.location, f"{DOMAIN}{url_for('users_show', user_id=self.testuser.id)}")

            msg = Message.query.order_by(Message.id.desc()).first()
            self.assertEqual(msg.text, "Hello")
            self.assertEqual(msg.user_id, self.testuser.id)
            self.assertEqual(msg.timestamp.strftime('%H %d %B %Y'),
                             cur_date.strftime('%H %d %B %Y'))

            resp2 = c.get(resp.location)
            html = resp2.get_data(as_text=True)

            self.assertEqual(resp2.status_code, 200)
            self.assertIn(
                '<div class="alert alert-success">Created message</div>', html)
            self.assertNotIn('<div class="alert alert-danger>', html)

    def test_view_message_non_user(self):
        """Can view a specific message as a non-user?"""

        # Since we are testing what it looks like as a non-user don't need to log in here

        with self.client as c:
            msg = self.testmsg_2
            resp = c.get(url_for('messages_show', message_id=msg.id))
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn('<div class="alert', html)
            self.assertIn(
                f'<a href="{url_for("users_show", user_id=msg.user_id)}"', html)
            self.assertIn(
                f'<img src="{msg.user.image_url}" alt="{msg.user.username} image"', html)
            self.assertIn(
                f'<a href="/users/{msg.user.id}">@{msg.user.username}</a>', html)
            self.assertNotIn(
                f'<form method="POST" action="/messages/{msg.id}/delete"', html)
            self.assertNotIn(
                f'<form method="POST" action="/users/stop-following/{msg.user.id}"', html)
            self.assertNotIn(
                f'<form method="POST" action="/users/follow/{msg.user.id}"', html)
            self.assertIn(f'<p class="single-message">{msg.text}</p>', html)
            self.assertNotIn(
                f'<form method="POST" action="/users/add_like/{msg.id}"', html)
            self.assertNotIn(
                f'<form method="POST" action="/users/remove_like/{msg.id}"', html)
            self.assertIn(
                f'<span class="text-muted">{msg.timestamp.strftime("%d %B %Y")}</span>', html)
            self.assertIn(f'<button class="btn btn-sm btn-secondary">', html)
            self.assertNotIn(f'<button class="btn btn-sm btn-primary">', html)
            self.assertIn(
                f'<span class="text-muted">{len(msg.liked_by)}</span>', html)

    def test_view_message_own_user(self):
        """Can view a specific message as the creator of the message?"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            msg = self.testmsg_2
            resp = c.get(url_for('messages_show', message_id=msg.id))
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn('<div class="alert', html)
            self.assertIn(
                f'<a href="{url_for("users_show", user_id=msg.user_id)}"', html)
            self.assertIn(
                f'<img src="{msg.user.image_url}" alt="{msg.user.username} image', html)
            self.assertIn(
                f'<a href="/users/{msg.user.id}">@{msg.user.username}</a>', html)
            self.assertIn(
                f'<form method="POST" action="/messages/{msg.id}/delete"', html)
            self.assertNotIn(
                f'<form method="POST" action="/users/stop-following/{msg.user.id}"', html)
            self.assertNotIn(
                f'<form method="POST" action="/users/follow/{msg.user.id}"', html)
            self.assertIn(f'<p class="single-message">{msg.text}</p>', html)
            self.assertNotIn(
                f'<form method="POST" action="/users/add_like/{msg.id}"', html)
            self.assertNotIn(
                f'<form method="POST" action="/users/remove_like/{msg.id}"', html)
            self.assertIn(
                f'<span class="text-muted">{msg.timestamp.strftime("%d %B %Y")}</span>', html)
            self.assertNotIn(
                f'<button class="btn btn-sm btn-secondary">', html)
            self.assertIn(f'<button class="btn btn-sm btn-primary">', html)
            self.assertIn(
                f'<span class="text-muted">{len(msg.liked_by)}</span>', html)

    def test_view_message_not_liked_not_following(self):
        """Can view a specific message as someone who hasn't like and isn't following?"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_2.id

            msg = self.testmsg
            resp = c.get(url_for('messages_show', message_id=msg.id))
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn('<div class="alert', html)
            self.assertIn(
                f'<a href="{url_for("users_show", user_id=msg.user_id)}"', html)
            self.assertIn(
                f'<img src="{msg.user.image_url}" alt="{msg.user.username} image', html)
            self.assertIn(
                f'<a href="/users/{msg.user.id}">@{msg.user.username}</a>', html)
            self.assertNotIn(
                f'<form method="POST" action="/messages/{msg.id}/delete"', html)
            self.assertNotIn(
                f'<form method="POST" action="/users/stop-following/{msg.user.id}"', html)
            self.assertIn(
                f'<form method="POST" action="/users/follow/{msg.user.id}"', html)
            self.assertIn(f'<p class="single-message">{msg.text}</p>', html)
            self.assertIn(
                f'<form method="POST" action="/users/add_like/{msg.id}"', html)
            self.assertNotIn(
                f'<form method="POST" action="/users/remove_like/{msg.id}"', html)
            self.assertIn(
                f'<span class="text-muted">{msg.timestamp.strftime("%d %B %Y")}</span>', html)
            self.assertIn(f'<button class="btn btn-sm btn-secondary">', html)
            self.assertNotIn(f'<button class="btn btn-sm btn-primary">', html)
            self.assertIn(
                f'<span class="text-muted">{len(msg.liked_by)}</span>', html)

    def test_view_message_not_liked_following(self):
        """Can view a specific message as someone who hasn't like and is following?"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            msg = self.testmsg_3
            resp = c.get(url_for('messages_show', message_id=msg.id))
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn('<div class="alert', html)
            self.assertIn(
                f'<a href="{url_for("users_show", user_id=msg.user_id)}"', html)
            self.assertIn(
                f'<img src="{msg.user.image_url}" alt="{msg.user.username} image', html)
            self.assertIn(
                f'<a href="/users/{msg.user.id}">@{msg.user.username}</a>', html)
            self.assertNotIn(
                f'<form method="POST" action="/messages/{msg.id}/delete"', html)
            self.assertIn(
                f'<form method="POST" action="/users/stop-following/{msg.user.id}"', html)
            self.assertNotIn(
                f'<form method="POST" action="/users/follow/{msg.user.id}"', html)
            self.assertIn(f'<p class="single-message">{msg.text}</p>', html)
            self.assertIn(
                f'<form method="POST" action="/users/add_like/{msg.id}"', html)
            self.assertNotIn(
                f'<form method="POST" action="/users/remove_like/{msg.id}"', html)
            self.assertIn(
                f'<span class="text-muted">{msg.timestamp.strftime("%d %B %Y")}</span>', html)
            self.assertIn(f'<button class="btn btn-sm btn-secondary">', html)
            self.assertNotIn(f'<button class="btn btn-sm btn-primary">', html)
            self.assertIn(
                f'<span class="text-muted">{len(msg.liked_by)}</span>', html)

    def test_view_message_liked_not_following(self):
        """Can view a specific message as someone who has like and isn't following?"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_2.id

            msg = self.testmsg_2
            resp = c.get(url_for('messages_show', message_id=msg.id))
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn('<div class="alert', html)
            self.assertIn(
                f'<a href="{url_for("users_show", user_id=msg.user_id)}"', html)
            self.assertIn(
                f'<img src="{msg.user.image_url}" alt="{msg.user.username} image', html)
            self.assertIn(
                f'<a href="/users/{msg.user.id}">@{msg.user.username}</a>', html)
            self.assertNotIn(
                f'<form method="POST" action="/messages/{msg.id}/delete"', html)
            self.assertNotIn(
                f'<form method="POST" action="/users/stop-following/{msg.user.id}"', html)
            self.assertIn(
                f'<form method="POST" action="/users/follow/{msg.user.id}"', html)
            self.assertIn(f'<p class="single-message">{msg.text}</p>', html)
            self.assertNotIn(
                f'<form method="POST" action="/users/add_like/{msg.id}"', html)
            self.assertIn(
                f'<form method="POST" action="/users/remove_like/{msg.id}"', html)
            self.assertIn(
                f'<span class="text-muted">{msg.timestamp.strftime("%d %B %Y")}</span>', html)
            self.assertNotIn(
                f'<button class="btn btn-sm btn-secondary">', html)
            self.assertIn(f'<button class="btn btn-sm btn-primary">', html)
            self.assertIn(
                f'<span class="text-muted">{len(msg.liked_by)}</span>', html)

    def test_view_message_liked_following(self):
        """Can view a specific message as someone who has like and is following?"""

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            msg = self.testmsg_4
            resp = c.get(url_for('messages_show', message_id=msg.id))
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn('<div class="alert', html)
            self.assertIn(
                f'<a href="{url_for("users_show", user_id=msg.user_id)}"', html)
            self.assertIn(
                f'<img src="{msg.user.image_url}" alt="{msg.user.username} image', html)
            self.assertIn(
                f'<a href="/users/{msg.user.id}">@{msg.user.username}</a>', html)
            self.assertNotIn(
                f'<form method="POST" action="/messages/{msg.id}/delete"', html)
            self.assertIn(
                f'<form method="POST" action="/users/stop-following/{msg.user.id}"', html)
            self.assertNotIn(
                f'<form method="POST" action="/users/follow/{msg.user.id}"', html)
            self.assertIn(f'<p class="single-message">{msg.text}</p>', html)
            self.assertNotIn(
                f'<form method="POST" action="/users/add_like/{msg.id}"', html)
            self.assertIn(
                f'<form method="POST" action="/users/remove_like/{msg.id}"', html)
            self.assertIn(
                f'<span class="text-muted">{msg.timestamp.strftime("%d %B %Y")}</span>', html)
            self.assertNotIn(
                f'<button class="btn btn-sm btn-secondary">', html)
            self.assertIn(f'<button class="btn btn-sm btn-primary">', html)
            self.assertIn(
                f'<span class="text-muted">{len(msg.liked_by)}</span>', html)
