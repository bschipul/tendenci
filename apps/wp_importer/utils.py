import os
import urllib2
import time
import uuid
import sys
from dateutil import parser
from datetime import datetime
from BeautifulSoup import BeautifulStoneSoup
from pages.models import Page
from articles.models import Article
from redirects.models import Redirect
from files.models import File
from django.contrib.auth.models import User
from django.conf import settings
from parse_uri import ParseUri

def get_posts(items, uri_parser, user):
    post_list = []
    redirect_list = []
    alreadyThere = False
    for node in items:
        post_type = node.find('wp:post_type').string
        post_status = node.find('wp:status').string

        if post_type == 'post' and post_status == 'publish':
            title = unicode(node.find('title').contents[0])
            body = unicode(node.find('content:encoded').contents[0])
            link = unicode(node.find('link').contents[0])
            slug = uri_parser.parse(link).path.strip('/')
            post_date = unicode(node.find('wp:post_date').contents[0])
            post_dt = datetime.strptime(post_date, '%Y-%m-%d %H:%M:%S')
            tags_raw = node.findAll('category', domain="post_tag")
            tags_list = []
            if tags_raw:
                for tag in tags_raw:
                    if len(','.join(tags_list)) + len(tag.string) <= 255:
                        tags_list.append(tag.string[:50])

            for post in Article.objects.all():
                if post.slug == slug[:100]:
                    alreadyThere = True
                    break
                else:
                    alreadyThere = False
            
            if not alreadyThere:
                post_list.append({
                    'headline': title,
                    'guid': str(uuid.uuid1()),
                    'slug': slug[:100],
                    'body': body,
                    'tags': ','.join(tags_list),
                    'timezone': 'US/Central',
                    'syndicate': True,
                    'featured': False,
                    'release_dt': post_dt,
                    'creator': user,
                    'creator_username': user.username,
                    'allow_anonymous_view': True,
                    'allow_user_view': False,
                    'allow_member_view': False,
                    'allow_anonymous_edit': False,
                    'allow_user_edit': False,
                    'allow_member_edit': False,
                    'owner': user,
                    'owner_username': user.username,
                    'status': True,
                    'status_detail': 'active'
                })

                redirect_list.append({
                    'from_url': slug[:100],
                    'to_url': os.path.join('articles', slug[:100])
                })

    return post_list, redirect_list
    

def get_pages(items, uri_parser, user):
    page_list = []
    alreadyThere = False
    for node in items:
        post_type = node.find('wp:post_type').string
        post_status = node.find('wp:status').string

        if post_type == 'page' and post_status == 'publish':
            title = unicode(node.find('title').contents[0])
            body = unicode(node.find('content:encoded').contents[0])
            link = unicode(node.find('link').contents[0])
            slug = uri_parser.parse(link).path.strip('/')

            for page in Page.objects.all():
                if page.slug == slug[:100]:
                    alreadyThere = True
                    break
                else:
                    alreadyThere = False
           
            if not alreadyThere:
                page_list.append({
                    'title': title,
                    'guid': str(uuid.uuid1()),
                    'slug': slug[:100],
                    'content': body,
                    #'timezone': 'US/Central',
                    'syndicate': True,
                    #'featured': False,
                    #'create_dt': datetime.now(), 
                    'creator': user,
                    'creator_username': user.username,
                    'allow_anonymous_view': True,
                    'allow_user_view': False,
                    'allow_member_view': False,
                    'allow_anonymous_edit': False,
                    'allow_user_edit': False,
                    'allow_member_edit': False,
                    'owner': user,
                    'owner_username': user.username,
                    'status': True,
                    'status_detail': 'active'
                })

    return page_list

def get_media(items, uri_parser, user):
    # from files.managers import save_files_for_instance
    ##################################################

    for node in items:
        post_type = node.find('wp:post_type').string
        if post_type == 'attachment':
            media_url = node.find('wp:attachment_url').string
            source = urllib2.urlopen(media_url).read()
            media_url = uri_parser.parse(media_url).file
            media_url = os.path.join(settings.MEDIA_ROOT, media_url)

            with open(media_url, 'wb') as f:
                f.write(source)
                file_path = f.name

            new_media = File(guid=unicode(uuid.uuid1()), file=file_path, creator=user, owner=user)
            new_media.save()

def run(file_name):
    f = open(file_name, 'r')
    xml = f.read()
    f.close()
    os.remove(file_name)

    uri_parser = ParseUri()
    soup = BeautifulStoneSoup(xml)
    items = soup.findAll('item')

    user = User.objects.get(id=1)

    get_media(items, uri_parser, user)
    posts = get_posts(items, uri_parser, user)[0]
    for post in posts:
        a = Article(**post)
        a.save()
    redirects = get_posts(items, uri_parser, user)[1]
    for redir in redirects:
        r = Redirect(**redir)
        r.save()
    pages = get_pages(items, uri_parser, user)
    for page in pages:
        p = Page(**page)
        p.save()
