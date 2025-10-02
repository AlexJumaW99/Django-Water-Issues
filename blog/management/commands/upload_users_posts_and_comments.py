import json
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from blog.models import Post, Comment
from water_issues_dashboard.models import Incident

class Command(BaseCommand):
    help = 'Load users, posts, and comments from JSON files into the database'

    def add_arguments(self, parser):
        parser.add_argument('--data-dir', type=str, help='Path to data directory', default='data')

    def handle(self, *args, **options):
        data_dir = options['data_dir']

        # File paths for the dummy data
        users_file = os.path.join(data_dir, 'users.json')
        posts_file = os.path.join(data_dir, 'posts.json')
        comments_file = os.path.join(data_dir, 'comments.json')

        # Load data
        self.load_users(users_file)
        self.load_posts(posts_file)
        self.load_comments(comments_file)

        self.stdout.write(self.style.SUCCESS('Successfully loaded all data.'))

    def load_users(self, filepath):
        if not os.path.exists(filepath):
            self.stdout.write(self.style.ERROR(f"File not found: {filepath}"))
            return

        with open(filepath, 'r') as f:
            users_data = json.load(f)

        count = 0
        for user_data in users_data:
            if not User.objects.filter(username=user_data['username']).exists():
                User.objects.create_user(
                    username=user_data['username'],
                    email=user_data['email'],
                    password=user_data['password']
                )
                count += 1

        self.stdout.write(self.style.SUCCESS(f"Loaded {count} new users from {filepath}"))

    def load_posts(self, filepath):
        if not os.path.exists(filepath):
            self.stdout.write(self.style.ERROR(f"File not found: {filepath}"))
            return

        with open(filepath, 'r') as f:
            posts_data = json.load(f)

        count = 0
        for post_data in posts_data:
            try:
                author = User.objects.get(username=post_data['author_username'])

                # Prepare post details
                post_details = {
                    'title': post_data['title'],
                    'content': post_data['content'],
                    'author': author
                }

                # Check for an associated incident ID
                if 'incident_id' in post_data:
                    try:
                        # Find the incident by its primary key (ID)
                        incident = Incident.objects.get(pk=post_data['incident_id'])
                        post_details['incident'] = incident
                    except Incident.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f"Incident with ID '{post_data['incident_id']}' not found for post '{post_data['title']}'. Post will be created without an incident link."))

                # Create the post if it doesn't exist
                if not Post.objects.filter(title=post_data['title'], author=author).exists():
                    Post.objects.create(**post_details)
                    count += 1

            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"User '{post_data['author_username']}' not found for post '{post_data['title']}'. Skipping."))

        self.stdout.write(self.style.SUCCESS(f"Loaded {count} new posts from {filepath}"))

    def load_comments(self, filepath):
        if not os.path.exists(filepath):
            self.stdout.write(self.style.ERROR(f"File not found: {filepath}"))
            return

        with open(filepath, 'r') as f:
            comments_data = json.load(f)

        count = 0
        for comment_data in comments_data:
            try:
                author = User.objects.get(username=comment_data['author_username'])
                post = Post.objects.get(title=comment_data['post_title'])

                if not Comment.objects.filter(content=comment_data['content'], author=author, post=post).exists():
                    Comment.objects.create(
                        content=comment_data['content'],
                        author=author,
                        post=post
                    )
                    count += 1
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"User '{comment_data['author_username']}' not found for a comment. Skipping."))
            except Post.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"Post with title '{comment_data['post_title']}' not found for a comment. Skipping."))

        self.stdout.write(self.style.SUCCESS(f"Loaded {count} new comments from {filepath}"))