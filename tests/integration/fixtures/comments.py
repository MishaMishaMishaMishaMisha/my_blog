import pytest
import pytest_asyncio
from source.models.comment import CommentModel
from source.core.utils import get_random_string


@pytest.fixture
def comment_json():

    return {
        "body": get_random_string(200),
        "parent_id": None,
        "files_id": [],
    }


@pytest.fixture
def comment_factory():

    def factory(
        *,
        author_id,
        post_id,
        body=None,
        parent_id=None,
        **kwargs,
    ):

        defaults = {
            "author_id": author_id,
            "post_id": post_id,
            "body": body or get_random_string(200),
            "parent_id": parent_id,
        }

        defaults.update(kwargs)

        return CommentModel(**defaults)

    return factory


@pytest_asyncio.fixture
async def comments_factory(
    db_session,
    comment_factory,
):

    async def factory(
        *,
        post,
        users,
        count: int = 1,
        parent_id=None,
        **kwargs,
    ):

        comments = []

        users_count = len(users)

        for i in range(count):

            comments.append(
                comment_factory(
                    author_id=users[i % users_count].id,
                    post_id=post.id,
                    parent_id=parent_id,
                    **kwargs,
                )
            )

        db_session.add_all(comments)

        await db_session.commit()

        for comment in comments:
            await db_session.refresh(comment)

        return comments

    return factory


@pytest_asyncio.fixture
async def comments_tree(
    comments_factory,
):

    async def factory(
        *,
        post,
        users,
        count_roots=2,
        count_replies_level1=2,
        count_replies_level2=2
    ):
        
        assert len(users) >= max(count_roots, count_replies_level1, count_replies_level2)

        roots = await comments_factory(
            post=post,
            users=users[:count_roots],
            count=count_roots,
        )

        # replies on 1 comment
        replies_lvl1 = await comments_factory(
            post=post,
            users=users[:count_replies_level1],
            count=count_replies_level1,
            parent_id=roots[0].id,
        )

        # replies on 1 reply on 1 comment
        replies_lvl2 = await comments_factory(
            post=post,
            users=users[:count_replies_level2],
            count=count_replies_level2,
            parent_id=replies_lvl1[0].id,
        )

        return {
            "roots": roots,
            "level1": replies_lvl1,
            "level2": replies_lvl2,
        }

    return factory