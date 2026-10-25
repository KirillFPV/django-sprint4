from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Post

POSTS_PER_PAGE = 10


def published_condition():
    return Q(
        is_published=True,
        pub_date__lte=timezone.now(),
        category__is_published=True,
    )


def get_published_posts(posts):
    return posts.filter(published_condition())


def get_page(request, posts):
    posts = posts.select_related('author', 'category', 'location').annotate(
        comment_count=Count('comments'),
    ).order_by('-pub_date')
    return Paginator(posts, POSTS_PER_PAGE).get_page(request.GET.get('page'))


def get_visible_post(request, post_id):
    condition = published_condition()
    if request.user.is_authenticated:
        condition |= Q(author=request.user)
    return get_object_or_404(
        Post.objects.select_related('author', 'category', 'location').filter(
            condition,
        ),
        pk=post_id,
    )
