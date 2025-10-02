from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Post, Like, Comment
from django.contrib.auth.models import User
from .forms import PostForm, CommentForm, IncidentPostForm
from users.forms import UserUpdateForm, ProfileUpdateForm
from django.http import JsonResponse, HttpResponseForbidden
import json
from water_issues_dashboard.models import Incident
from django.contrib import messages

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
    profile_user = get_object_or_404(User, id=user_id)
    posts = Post.objects.filter(author=profile_user).order_by('-date_posted')
    
    if request.method == 'POST' and request.user == profile_user:
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        post_form = PostForm(request.POST)
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, f'Your account has been updated!')
            return redirect('blog-profile', user_id=profile_user.id)

        if post_form.is_valid():
            post = post_form.save(commit=False)
            post.author = request.user
            post.save()
            messages.success(request, f'Your post has been created!')
            return redirect('blog-profile', user_id=profile_user.id)

    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)
        post_form = PostForm()

    context = {
        'profile_user': profile_user,
        'posts': posts,
        'u_form': u_form,
        'p_form': p_form,
        'post_form': post_form
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

@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user != post.author:
        return HttpResponseForbidden()
    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Your post has been deleted.')
        return redirect('blog-home')
    return render(request, 'blog/confirm_delete.html', {'object': post})

@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if request.user != comment.author:
        return HttpResponseForbidden()
    if request.method == 'POST':
        post_id = comment.post.id
        comment.delete()
        messages.success(request, 'Your comment has been deleted.')
        return redirect('blog-post', post_id=post_id)
    return render(request, 'blog/confirm_delete.html', {'object': comment})