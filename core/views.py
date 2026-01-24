from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, Q, Exists, OuterRef
from .models import Post, Comment, Reaction, Report
from .forms import PostForm, CommentForm
from .ai_service import ai_analyzer

from django.utils import timezone
from datetime import timedelta

def post_list(request):
    # Sorting and Filtering
    sort_by = request.GET.get('sort', 'newest')
    time_filter = request.GET.get('time', 'all')
    
    posts = Post.objects.filter(is_flagged=False)

    # Post Type Filter (supports multiple)
    post_types = request.GET.getlist('type')
    if post_types:
        posts = posts.filter(post_type__in=post_types)
    
    # Time Filter
    if time_filter != 'all':
        now = timezone.now()
        if time_filter == 'day':
            start_date = now - timedelta(days=1)
        elif time_filter == 'week':
            start_date = now - timedelta(weeks=1)
        elif time_filter == 'month':
            start_date = now - timedelta(days=30)
        elif time_filter == 'year':
            start_date = now - timedelta(days=365)
        else:
            start_date = None
            
        if start_date:
            posts = posts.filter(created_at__gte=start_date)

    # Sorting
    if sort_by == 'popular':
        # Annotate with like count for sorting
        posts = posts.annotate(total_likes=Count('reactions', filter=Q(reactions__reaction_type=Reaction.LIKE))).order_by('-total_likes', '-created_at')
    elif sort_by == 'most_commented':
        posts = posts.annotate(total_comments=Count('comments')).order_by('-total_comments', '-created_at')
    else: # newest
        posts = posts.order_by('-created_at')
    
    # Optional: Basic search
    query = request.GET.get('q')
    if query:
        posts = posts.filter(
            Q(content__icontains=query) | Q(tags__name__icontains=query)
        ).distinct()

    # Annotate with is_liked for current session
    if not request.session.session_key:
        request.session.create()
    session_id = request.session.session_key

    is_liked_subquery = Reaction.objects.filter(
        post=OuterRef('pk'),
        session_id=session_id,
        reaction_type=Reaction.LIKE
    )
    posts = posts.annotate(is_liked=Exists(is_liked_subquery))
    
    return render(request, 'core/post_list.html', {
        'posts': posts,
        'current_sort': sort_by,
        'current_time': time_filter,
        'selected_types': post_types
    })

def static_page(request, page_name):
    # Generic view for static pages to avoid creating many separate views
    # Ensure page_name is safe or whitelist it
    valid_pages = ['about', 'mission', 'faq', 'legal', 'security', 'safety']
    if page_name not in valid_pages:
        return redirect('post_list')
        
    context = {'page_name': page_name}
    return render(request, 'core/static_page.html', context)

def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            
            # AI Analysis
            analysis = ai_analyzer.analyze_post(post.content, post.image)
            
            if not analysis['is_safe']:
                # Reject or flag (User wanted "filters out", so maybe just don't save or save as flagged)
                # Let's save as flagged and show a message (or just silently fail/redirect)
                post.is_flagged = True
                post.save()
                # Ideally, give feedback
                return render(request, 'core/create_post.html', {'form': form, 'error': analysis['flag_reason']})
            
            post.save()
            
            # Add tags
            for tag_name in analysis['tags']:
                from .models import Tag
                tag, _ = Tag.objects.get_or_create(name=tag_name)
                post.tags.add(tag)

            # Track for notifications
            my_posts = request.session.get('my_posts', [])
            my_posts.append(str(post.id))
            request.session['my_posts'] = my_posts
            request.session.modified = True
                
            return redirect('post_list')
    else:
        form = PostForm()
    
    return render(request, 'core/create_post.html', {'form': form})

def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    comments = post.comments.order_by('created_at')
    
    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.post = post
            comment.save()
            return redirect('post_detail', pk=pk)
    else:
        comment_form = CommentForm()

    # Check if liked
    if not request.session.session_key:
        request.session.create()
    session_id = request.session.session_key
    
    is_liked = Reaction.objects.filter(
        post=post,
        session_id=session_id,
        reaction_type=Reaction.LIKE
    ).exists()

    return render(request, 'core/post_detail.html', {
        'post': post,
        'comments': comments,
        'comment_form': comment_form,
        'is_liked': is_liked
    })

def like_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    
    # Basic Anon Session Tracking
    if not request.session.session_key:
        request.session.create()
    session_id = request.session.session_key
    
    # Toggle like
    reaction, created = Reaction.objects.get_or_create(
        post=post,
        session_id=session_id,
        reaction_type=Reaction.LIKE
    )
    
    if not created:
        # If already liked, unlike (delete)
        reaction.delete()
        is_liked = False
    else:
        is_liked = True

    # Check for AJAX request
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        from django.http import JsonResponse
        return JsonResponse({
            'liked': is_liked,
            'count': post.reactions.filter(reaction_type=Reaction.LIKE).count()
        })
        
    # Return to previous page
    return redirect(request.META.get('HTTP_REFERER', 'post_list'))

def add_comment(request, pk):
    # Handled in post_detail usually, but if called directly:
    return redirect('post_detail', pk=pk)

def report_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', 'other')
        if not request.session.session_key:
            request.session.create()
        session_id = request.session.session_key
        
        # Prevent duplicate reports from same session
        if not Report.objects.filter(post=post, session_id=session_id).exists():
            Report.objects.create(
                post=post,
                reason=reason,
                session_id=session_id
            )
        
        # Determine redirect (AJAX vs Standard)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            from django.http import JsonResponse
            return JsonResponse({'status': 'reported'})
            
    return redirect(request.META.get('HTTP_REFERER', 'post_list'))

# Helper for context processor
def get_notification_count(request):
    if not request.session.get('my_posts'):
        return 0
    
    my_post_ids = request.session.get('my_posts', [])
    total_comments = Comment.objects.filter(post__id__in=my_post_ids).count()
    last_seen = request.session.get('last_seen_comments_count', 0)
    
    return max(0, total_comments - last_seen)

def clear_notifications(request):
    if request.method == 'POST':
        my_post_ids = request.session.get('my_posts', [])
        total_comments = Comment.objects.filter(post__id__in=my_post_ids).count()
        request.session['last_seen_comments_count'] = total_comments
        request.session.modified = True
        return redirect(request.META.get('HTTP_REFERER', 'post_list'))
    return redirect('post_list')
