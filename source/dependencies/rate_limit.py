from fastapi_limiter.depends import RateLimiter
from fastapi import FastAPI
from fastapi.routing import APIRoute

from source.core.utils import custom_rate_limit_callback

# users
register_rate_limiter = RateLimiter(times=2, seconds=5)
get_me_limiter = RateLimiter(times=5, seconds=10)
get_users_limiter = RateLimiter(times=2, seconds=5)
find_users_limiter = RateLimiter(times=1, seconds=5)
get_user_profile_limiter = RateLimiter(times=2, seconds=5)
get_user_posts_limiter = RateLimiter(times=2, seconds=5)
delete_user_limiter = RateLimiter(times=1, seconds=10)
update_user_limiter = RateLimiter(times=2, seconds=5)
update_password_limiter = RateLimiter(times=2, seconds=10)
update_email_limiter = RateLimiter(times=2, seconds=10)

# auth
login_limiter = RateLimiter(times=2, seconds=5, callback=custom_rate_limit_callback)
logout_limiter = RateLimiter(times=1, seconds=5)
refresh_token_limiter = RateLimiter(times=1, seconds=5)
resend_verify_email_limiter = RateLimiter(times=1, seconds=60)
verify_email_limiter = RateLimiter(times=1, seconds=10)
forgot_password_email_limiter = RateLimiter(times=1, seconds=20)
reset_password_limiter = RateLimiter(times=1, seconds=10)

# uploads
upload_limiter = RateLimiter(times=2, seconds=5)

# posts
create_post_limiter = RateLimiter(times=2, seconds=10)
get_posts_limiter = RateLimiter(times=2, seconds=5)
react_to_post_limiter = RateLimiter(times=2, seconds=5)
get_tags_limiter = RateLimiter(times=2, seconds=5)
find_posts_limiter = RateLimiter(times=2, seconds=5)
find_tags_limiter = RateLimiter(times=5, seconds=5)
find_posts_with_tag_limiter = RateLimiter(times=2, seconds=5)
delete_post_limiter = RateLimiter(times=2, seconds=5)
update_post_limiter = RateLimiter(times=2, seconds=10)
get_post_limiter = RateLimiter(times=2, seconds=5)

# comments
create_comment_limiter = RateLimiter(times=2, seconds=10)
get_root_comments_limiter = RateLimiter(times=2, seconds=5)
get_root_replies_limiter = RateLimiter(times=2, seconds=5)
react_to_comment_limiter = RateLimiter(times=2, seconds=5)
delete_comment_limiter = RateLimiter(times=2, seconds=5)
update_comment_limiter = RateLimiter(times=2, seconds=10)


async def disable_rate_limiter():
    pass

def disable_all_rate_limiters(app: FastAPI):
    print("disabling rate limiters...")
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        for dependency in route.dependant.dependencies:
            if isinstance(dependency.call, RateLimiter):
                app.dependency_overrides[dependency.call] = disable_rate_limiter
    