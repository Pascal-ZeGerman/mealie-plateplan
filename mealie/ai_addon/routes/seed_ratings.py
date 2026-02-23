from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from mealie.ai_addon.db.models import AiAddonSeedRating
from mealie.ai_addon.schema.preferences import SeedRatingsSubmit
from mealie.core.dependencies.dependencies import get_current_user
from mealie.db.db_setup import generate_session
from mealie.schema.user import PrivateUser

router = APIRouter(prefix="/preferences/seed-ratings")


@router.post("", status_code=status.HTTP_201_CREATED)
def submit_seed_ratings(
    payload: SeedRatingsSubmit,
    current_user: PrivateUser = Depends(get_current_user),
    session: Session = Depends(generate_session),
) -> dict:
    """Accept a batch of seed recipe ratings for the authenticated user (ONB-02).

    For each rating: update an existing record if one exists for the same
    user_id + recipe_slug pair, otherwise create a new one.
    All records are committed in a single transaction.
    """
    user_id = str(current_user.id)

    for rating_in in payload.ratings:
        existing = (
            session.query(AiAddonSeedRating)
            .filter_by(user_id=user_id, recipe_slug=rating_in.recipe_slug)
            .first()
        )
        if existing is not None:
            existing.recipe_name = rating_in.recipe_name
            existing.rating = rating_in.rating
        else:
            new_rating = AiAddonSeedRating(
                user_id=user_id,
                recipe_slug=rating_in.recipe_slug,
                recipe_name=rating_in.recipe_name,
                rating=rating_in.rating,
            )
            session.add(new_rating)

    session.commit()
    return {"saved": len(payload.ratings)}
