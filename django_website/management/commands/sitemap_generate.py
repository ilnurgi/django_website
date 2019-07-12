"""
генератор sitemap
"""
import os
from datetime import date

from django.conf import settings
from django.core.mail import mail_admins
from django.core.management import BaseCommand
from django.template import loader as template_loader


from django_gii_blog.models import Post


def error(func):
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as err:
            import traceback
            mail_admins(
                'DJANGO_WEBSITE_SITEMAP_GENERATOR',
                'ERROR:\n{0}\n{1}'.format(
                    str(err),
                    str(traceback.format_exc())
                )
            )
            raise
    return inner


class Command(BaseCommand):
    """
    геренатор
    """

    SITEMAP_NAME = 'sitemap_{host}.xml'
    SITEMAP_DIR = settings.MEDIA_ROOT
    DOCS_DIR = settings.DOCS_DIR

    def get_docs(self):
        """
        собираем сведения по документации
        """
        docs = []
        exclude_dirs = ('.git', '.idea', '.vscode')
        docs_dir_length = len(self.DOCS_DIR)
        for root, dirs, files in os.walk(self.DOCS_DIR):
            if any(excl in root for excl in exclude_dirs):
                continue

            base_path = root[docs_dir_length:]
            for file_name in files:
                if not file_name.endswith('.rst'):
                    continue

                docs.append({
                    'file_path': os.path.join(base_path, file_name.replace('.rst', '.html')).replace('\\', '/'),
                    'updated': date.fromtimestamp(os.stat(os.path.join(root, file_name)).st_mtime)
                })

        return docs

    def get_context(self, host, posts, docs, post_max_date, docs_max_date):
        """
        формируем строку шаблоны для файла
        :param host: хост
        :param posts: посты
        :param docs: конспекты
        :rtype: dict
        """
        url_set = [
            {
                'location': 'http://{host}/blog/'.format(host=host),
                'lastmod': post_max_date,
                'changefreq': 'monthly',
                'priority': 0.5,
            },
            {
                'location': 'http://{host}/docs/index.html'.format(host=host),
                'lastmod': docs_max_date,
                'changefreq': 'monthly',
                'priority': 0.5,
            },
        ]
        url_set.extend(
            {
                'location': 'http://{host}/blog/{post_id}'.format(host=host, post_id=post.id),
                'lastmod': post.updated,
                'changefreq': 'monthly',
                'priority': 0.5,
            }
            for post in posts
        )
        url_set.extend(
            {
                'location': 'http://{host}/docs/{file_path}'.format(host=host, file_path=doc['file_path']),
                'lastmod': doc['updated'],
                'changefreq': 'monthly',
                'priority': 0.5,
            }
            for doc in docs
        )
        return {
            'urlset': url_set
        }

    @error
    def handle(self, *args, **options):
        """
        обработчик
        """

        posts = Post.objects.filter(published=True)
        post_max_date = max(post.updated for post in posts)

        docs = self.get_docs()
        docs_max_date = post_max_date

        sitemap_template = template_loader.get_template('sitemap.xml')
        for host in (
                'www.ilnurgi.ru',
                'ilnurgi.ru',
                'www.ilnurgi1.ru',
                'ilnurgi1.ru',
        ):
            sitemap_data = sitemap_template.render(self.get_context(host, posts, docs, post_max_date, docs_max_date))
            open(os.path.join(self.SITEMAP_DIR, self.SITEMAP_NAME.format(host=host)), 'w').write(sitemap_data)
