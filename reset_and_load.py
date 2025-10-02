#!/usr/bin/env python
import os
import subprocess
import shutil
from django.core.management import call_command
from django.core.wsgi import get_wsgi_application

def main():
    """
    Automates the process of resetting the Django database, applying migrations,
    loading initial data, and creating a superuser.
    """
    # --- Configuration ---
    # Add your Django app names here
    DJANGO_APPS = [
        'blog',
        'users',
        'water_issues_dashboard'
    ]
    DB_NAME = 'db.sqlite3'
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # Superuser credentials
    SUPERUSER_USERNAME = 'ajuma'
    SUPERUSER_EMAIL = 'jumalex99@gmail.com'
    SUPERUSER_PASSWORD = 'Aj37024013!'

    # --- 1. Clean Migrations ---
    print("--- Cleaning migration files ---")
    for app in DJANGO_APPS:
        migrations_dir = os.path.join(BASE_DIR, app, 'migrations')
        if os.path.exists(migrations_dir):
            for filename in os.listdir(migrations_dir):
                if filename != '__init__.py' and not filename.endswith('.pyc'):
                    file_path = os.path.join(migrations_dir, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(f"Deleted migration file: {file_path}")
            # Also remove the __pycache__ directory if it exists
            pycache_path = os.path.join(migrations_dir, '__pycache__')
            if os.path.exists(pycache_path):
                shutil.rmtree(pycache_path)
                print(f"Deleted __pycache__: {pycache_path}")

    # --- 2. Delete Database ---
    print(f"\n--- Deleting database: {DB_NAME} ---")
    db_path = os.path.join(BASE_DIR, DB_NAME)
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Successfully deleted {DB_NAME}")

    # --- 3. Run Initial Management Commands ---
    print("\n--- Running Django management commands ---")

    # Set up Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recap.settings')
    application = get_wsgi_application()

    commands = [
        "makemigrations",
        "migrate",
        "load_initial_data",
        "upload_users_posts_and_comments"
    ]

    for command in commands:
        print(f"\n--- Running: django-admin {command} ---")
        try:
            call_command(command)
        except Exception as e:
            print(f"An error occurred while running command: {command}")
            print(e)
            return

    # --- 4. Create Superuser ---
    print(f"\n--- Creating superuser: {SUPERUSER_USERNAME} ---")
    from django.contrib.auth import get_user_model
    User = get_user_model()

    if not User.objects.filter(username=SUPERUSER_USERNAME).exists():
        User.objects.create_superuser(SUPERUSER_USERNAME, SUPERUSER_EMAIL, SUPERUSER_PASSWORD)
        print(f"Superuser '{SUPERUSER_USERNAME}' created successfully.")
    else:
        print(f"Superuser '{SUPERUSER_USERNAME}' already exists.")


    print("\n--- Automation script finished successfully! ---")

if __name__ == "__main__":
    main()