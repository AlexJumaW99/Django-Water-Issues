from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Post, Like
from django.contrib.auth.models import User
from .forms import PostForm, CommentForm, IncidentPostForm
from django.http import JsonResponse
import json
from water_issues_dashboard.models import Incident

@login_required
def home(request):
    posts = Post.objects.all().order_by('-date_posted')
    if request.user.is_authenticated:
        liked_post_ids = Like.objects.filter(user=request.user).values_list('post_id', flat=True)
    else:
        liked_post_ids = []

    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('blog-home')
    else:
        form = PostForm()

    context = {
        'posts': posts,
        'form': form,
        'liked_post_ids': liked_post_ids,
    }
    return render(request, 'blog/home.html', context)

@login_required
def about(request):
    return render(request, 'blog/about.html', {'title': 'About'})

@login_required
def post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    comments = post.comments.all().order_by('-date_posted')
    
    is_liked = False
    if request.user.is_authenticated:
        if Like.objects.filter(post=post, user=request.user).exists():
            is_liked = True

    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.post = post
            new_comment.author = request.user
            new_comment.save()
            return redirect('blog-post', post_id=post.id)
    else:
        comment_form = CommentForm()

    context = {
        'post': post,
        'comments': comments,
        'comment_form': comment_form,
        'is_liked': is_liked,
    }
    return render(request, 'blog/post.html', context)

@login_required
def profile(request, user_id):
    user = get_object_or_404(User, id=user_id)
    posts = Post.objects.filter(author=user).order_by('-date_posted')
    context = {
        'user': user,
        'posts': posts,
    }
    return render(request, 'blog/profile.html', context)

def landing(request):
    return render(request, 'blog/landing.html', {'title': 'Welcome'})

@login_required
def like_post(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        post_id = data.get('post_id')
        post = get_object_or_404(Post, id=post_id)
        
        like, created = Like.objects.get_or_create(user=request.user, post=post)

        if not created:
            like.delete()
            liked = False
        else:
            liked = True
        
        return JsonResponse({'liked': liked, 'likes_count': post.number_of_likes})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def incident_discussion(request, incident_id):
    incident = get_object_or_404(Incident, id=incident_id)
    posts = incident.posts.all().order_by('-date_posted')
    liked_post_ids = []
    if request.user.is_authenticated:
        liked_post_ids = Like.objects.filter(user=request.user, post__in=posts).values_list('post_id', flat=True)

    if request.method == 'POST':
        form = IncidentPostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.incident = incident
            post.save()
            return redirect('incident-discussion', incident_id=incident.id)
    else:
        form = IncidentPostForm()

    context = {
        'incident': incident,
        'posts': posts,
        'form': form,
        'liked_post_ids': liked_post_ids
    }
    return render(request, 'blog/incident_discussion.html', context)