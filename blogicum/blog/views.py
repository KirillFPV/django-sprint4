from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .forms import CommentForm, PostForm, ProfileForm
from .models import Category, Comment, Post
from .utils import get_page, get_published_posts, get_visible_post

User = get_user_model()


def index(request):
    posts = get_published_posts(Post.objects.all())
    return render(request, 'blog/index.html', {
        'page_obj': get_page(request, posts),
    })


def post_detail(request, post_id):
    post = get_visible_post(request, post_id)
    return render(request, 'blog/detail.html', {
        'post': post,
        'form': CommentForm(),
        'comments': post.comments.select_related('author'),
    })


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category, slug=category_slug, is_published=True,
    )
    posts = get_published_posts(category.posts.all())
    return render(request, 'blog/category.html', {
        'category': category,
        'page_obj': get_page(request, posts),
    })


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = author.posts.all()
    if request.user != author:
        posts = get_published_posts(posts)
    return render(request, 'blog/profile.html', {
        'profile': author,
        'page_obj': get_page(request, posts),
    })


@login_required
@require_http_methods(['GET', 'POST'])
def edit_profile(request):
    form = ProfileForm(
        request.POST if request.method == 'POST' else None,
        instance=request.user,
    )
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        return redirect('blog:profile', username=user.username)
    return render(request, 'blog/user.html', {'form': form})


@login_required
@require_http_methods(['GET', 'POST'])
def create_post(request):
    form = PostForm(
        request.POST if request.method == 'POST' else None,
        request.FILES if request.method == 'POST' else None,
    )
    if request.method == 'POST' and form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:profile', username=request.user.username)
    return render(request, 'blog/create.html', {'form': form})


@login_required
@require_http_methods(['GET', 'POST'])
def edit_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)
    form = PostForm(
        request.POST if request.method == 'POST' else None,
        request.FILES if request.method == 'POST' else None,
        instance=post,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, 'blog/create.html', {'form': form})


@login_required
@require_http_methods(['GET', 'POST'])
def delete_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)
    if request.method == 'POST':
        post.delete()
        return redirect('blog:index')
    return render(request, 'blog/create.html', {
        'form': PostForm(instance=post),
    })


@login_required
@require_POST
def add_comment(request, post_id):
    post = get_visible_post(request, post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, 'blog/detail.html', {
        'post': post,
        'form': form,
        'comments': post.comments.select_related('author'),
    })


@login_required
@require_http_methods(['GET', 'POST'])
def edit_comment(request, post_id, comment_id):
    comment = get_object_or_404(
        Comment, pk=comment_id, post_id=post_id, author=request.user,
    )
    form = CommentForm(
        request.POST if request.method == 'POST' else None, instance=comment,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, 'blog/comment.html', {
        'comment': comment, 'form': form,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def delete_comment(request, post_id, comment_id):
    comment = get_object_or_404(
        Comment, pk=comment_id, post_id=post_id, author=request.user,
    )
    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, 'blog/comment.html', {'comment': comment})
