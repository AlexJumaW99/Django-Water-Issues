#!/usr/bin/env python
import os
import subprocess
import shutil

def main():
    """
    Automates the process of resetting the Django database, applying migrations,
    and loading initial data.
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

    # --- 3. Run Management Commands ---
    print("\n--- Running Django management commands ---")
    commands = [
        "python manage.py makemigrations",
        "python manage.py migrate",
        "python manage.py load_initial_data",
        "python manage.py upload_users_posts_and_comments"
    ]

    for command in commands:
        print(f"\n--- Running: {command} ---")
        try:
            subprocess.run(command, shell=True, check=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"An error occurred while running command: {command}")
            print(e)
            return


    print("\n--- Automation script finished successfully! ---")

if __name__ == "__main__":
    main()