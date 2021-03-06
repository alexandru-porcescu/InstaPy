"""OS Modules environ method to get the setup vars from the Environment"""
from os import environ
from random import randint
from time import sleep
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException

from .clarifai_util import check_image
from .comment_util import comment_image
from .like_util import check_link
from .like_util import get_links_for_tag
from .like_util import get_tags
from .like_util import like_image
from .login_util import login_user
from .unfollow_util import unfollow
from .unfollow_util import follow_user

class InstaPy:
  """Class to be instantiated to use the script"""
  def __init__(self, username=None, password=None):
    self.browser = webdriver.Chrome('./assets/chromedriver')
    if username is None:
      self.username = environ.get('INSTA_USER')
    else:
      self.username = username

    if password is None:
      self.password = environ.get('INSTA_PW')
    else:
      self.password = password

    self.do_comment = False
    self.comment_percentage = 0
    self.comments = ['Cool!', 'Nice!', 'Looks good!']

    self.do_follow = False
    self.follow_percentage = 0
    self.dont_include = []

    self.dont_like = ['sex', 'nsfw']
    self.ignore_if_contains = []

    self.use_clarifai = False
    self.clarifai_secret = None
    self.clarifai_id = None
    self.clarifai_img_tags = []

    self.aborting = False

  def login(self):
    """Used to login the user either with the username and password"""
    if not login_user(self.browser, self.username, self.password):
      print('Wrong login data!')
      self.aborting = True
    else:
      print('Logged in successfully!')

    return self

  def set_do_comment(self, enabled=False, percentage=0):
    """Defines if images should be commented or not
    percentage=25 -> ~ every 4th picture will be commented"""
    if self.aborting:
      return self

    self.do_comment = enabled
    self.comment_percentage = percentage

    return self

  def set_comments(self, comments=None):
    """Changes the possible comments"""
    if self.aborting:
      return self

    if comments is None:
      comments = []
    self.comments = comments

    return self

  def set_do_follow(self, enabled=False, percentage=0):
    """Defines if the user of the liked image should be followed"""
    if self.aborting:
      return self

    self.do_follow = enabled
    self.follow_percentage = percentage

    return self

  def set_dont_like(self, tags=None):
    """Changes the possible restriction tags, if one of this
     words is in the description, the image won't be liked"""
    if self.aborting:
      return self

    if tags is None:
      tags = []
    self.dont_like = tags

    return self

  def set_ignore_if_contains(self, words=None):
    """ignores the don't likes if the description contains
    one of the given words"""
    if self.aborting:
      return self

    if words is None:
      words = []
    self.ignore_if_contains = words

    return self

  def set_dont_include(self, friends=None):
    """Defines which accounts should not be unfollowed"""
    if self.aborting:
      return self

    if friends is None:
      friends = []
    self.dont_include = friends

    return self

  def set_use_clarifai(self, enabled=False, secret=None, proj_id=None):
    """Defines if the clarifai img api should be used
    Which 'project' will be used (only 5000 calls per month)"""
    if self.aborting:
      return self

    self.use_clarifai = enabled

    if secret is None and self.clarifai_secret is None:
      self.clarifai_secret = environ.get('CLARIFAI_SECRET')
    elif secret is not None:
      self.clarifai_secret = secret

    if proj_id is None and self.clarifai_id is None:
      self.clarifai_id = environ.get('CLARIFAI_ID')
    elif proj_id is not None:
      self.clarifai_id = proj_id

    return self

  def clarifai_check_img_for(self, tags=None, comment=False, comments=None):
    """Defines the tags, the images should be checked for"""
    if self.aborting:
      return self

    if tags is None and not self.clarifai_img_tags:
      self.use_clarifai = False
    elif tags:
      self.clarifai_img_tags.append((tags, comment, comments))

    return self

  def like_by_tags(self, tags=None, amount=50):
    """Likes (default) 50 images per given tag"""
    if self.aborting:
      return self

    liked_img = 0
    already_liked = 0
    inap_img = 0
    commented = 0
    followed = 0

    if tags is None:
      tags = []

    for index, tag in enumerate(tags):
      print('Tag [%d/%d]' % (index + 1, len(tags)))
      print('--> ' + tag)
      try:
        links = get_links_for_tag(self.browser, tag, amount)
      except NoSuchElementException:
        print('Too few images, aborting')
        self.aborting = True
        return self

      for i, link in enumerate(links):
        print('[%d/%d]' % (i + 1, len(links)))
        try:
          inappropriate, user_name = \
            check_link(self.browser, link, self.dont_like,
                       self.ignore_if_contains, self.username)

          if not inappropriate:
            liked = like_image(self.browser)

            if liked:
              liked_img += 1
              checked_img = True
              temp_comments = []
              commenting = True if randint(0, 100) <= self.comment_percentage\
                          else False
              following = True if randint(0, 100) <= self.follow_percentage\
                          else False

              if self.use_clarifai and (following or commenting):
                try:
                  checked_img, temp_comments =\
                    check_image(self.browser, self.clarifai_id,
                                self.clarifai_secret,
                                self.clarifai_img_tags)
                except Exception as err:
                  print('Image check error: ' + str(err))

              if self.do_comment and user_name not in self.dont_include \
                  and checked_img and commenting:
                commented += comment_image(self.browser,
                                           temp_comments if temp_comments
                                           else self.comments)
              else:
                print('--> Not commented')
                sleep(1)

              if self.do_follow and user_name not in self.dont_include \
                  and checked_img and following:
                followed += follow_user(self.browser)
              else:
                print('--> Not following')
                sleep(1)
            else:
              already_liked += 1
          else:
            print('Image not liked: Inappropriate')
            inap_img += 1
        except NoSuchElementException as err:
          print('Invalid Page: ' + str(err))
        print('')

    print('Liked: ' + str(liked_img))
    print('Already Liked: ' + str(already_liked))
    print('Inappropriate: ' + str(inap_img))
    print('Commented: ' + str(commented))
    print('Followed: ' + str(followed))

    return self

  def like_from_image(self, url, amount=50):
    """Gets the tags from an image and likes 50 images for each tag"""
    if self.aborting:
      return self

    try:
      tags = get_tags(self.browser, url)
      print(tags)
      self.like_by_tags(tags, amount)
    except TypeError as err:
      print('Sorry, an error occured: ' + str(err))
      self.aborting = True
      return self

    return self

  def unfollow_users(self, amount=10):
    """Unfollows (default) 10 users from your following list"""
    while amount > 0:
      try:
        unfollow(self.browser, self.username, amount)
      except TypeError as err:
        print('Sorry, an error occured: ' + str(err))
        self.aborting = True
        return self

      if amount > 10:
        sleep(600)
        print('Sleeping for 10min')

      amount -= 10

    return self

  def end(self):
    """Closes the current session"""
    self.browser.delete_all_cookies()
    self.browser.close()
    print('')
    print('Session ended')
    print('-------------')
