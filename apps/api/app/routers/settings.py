"""Settings API: profile, contacts, phrases, call history. The app talks only to this API."""

from fastapi import APIRouter, Depends, HTTPException

from app.auth import current_user
from app.models.api import ContactIn, PhraseIn, ProfileIn
from app.specs import load_json
from app.store import Profile, Store, get_store

router = APIRouter(tags=["settings"])


def profile_json(p: Profile) -> dict:
    return {
        "display_name": p.display_name if p.onboarded else "",
        "preset": p.preset,
        "talk_modes": p.talk_modes,
        "hear_modes": p.hear_modes,
        "read_lang": p.read_lang,
        "type_lang": p.type_lang,
        "easy_font": p.easy_font,
        "speech_rate": p.speech_rate,
    }


@router.get("/v1/me")
async def get_me(user_id: str = Depends(current_user), store: Store = Depends(get_store)) -> dict:
    p = await store.get_profile(user_id)
    return {
        "onboarded": p.onboarded,
        "profile": profile_json(p),
        "presets": load_json("data/presets.json"),
    }


@router.put("/v1/me")
async def put_me(
    body: ProfileIn, user_id: str = Depends(current_user), store: Store = Depends(get_store)
) -> dict:
    await store.put_profile(
        Profile(
            user_id=user_id,
            display_name=body.display_name,
            preset=body.preset,
            talk_modes=list(body.talk_modes),
            hear_modes=list(body.hear_modes),
            read_lang=body.read_lang,
            type_lang=body.type_lang,
            easy_font=body.easy_font,
            speech_rate=body.speech_rate,
        )
    )
    return await get_me(user_id, store)


@router.get("/v1/contacts")
async def list_contacts(
    user_id: str = Depends(current_user), store: Store = Depends(get_store)
) -> list[dict]:
    return await store.list_contacts(user_id)


@router.post("/v1/contacts", status_code=201)
async def add_contact(
    body: ContactIn, user_id: str = Depends(current_user), store: Store = Depends(get_store)
) -> dict:
    return await store.save_contact(user_id, body.model_dump(exclude_none=False))


@router.put("/v1/contacts/{contact_id}")
async def update_contact(
    contact_id: str,
    body: ContactIn,
    user_id: str = Depends(current_user),
    store: Store = Depends(get_store),
) -> dict:
    try:
        return await store.save_contact(user_id, body.model_dump(), contact_id)
    except KeyError as exc:
        raise HTTPException(status_code=404) from exc


@router.delete("/v1/contacts/{contact_id}", status_code=204)
async def delete_contact(
    contact_id: str, user_id: str = Depends(current_user), store: Store = Depends(get_store)
) -> None:
    await store.delete_contact(user_id, contact_id)


@router.get("/v1/phrases")
async def list_phrases(
    user_id: str = Depends(current_user), store: Store = Depends(get_store)
) -> list[dict]:
    return await store.list_phrases(user_id)


@router.post("/v1/phrases", status_code=201)
async def add_phrase(
    body: PhraseIn, user_id: str = Depends(current_user), store: Store = Depends(get_store)
) -> dict:
    return await store.save_phrase(user_id, body.model_dump())


@router.delete("/v1/phrases/{phrase_id}", status_code=204)
async def delete_phrase(
    phrase_id: str, user_id: str = Depends(current_user), store: Store = Depends(get_store)
) -> None:
    await store.delete_phrase(user_id, phrase_id)


@router.get("/v1/calls")
async def call_history(
    user_id: str = Depends(current_user), store: Store = Depends(get_store)
) -> list[dict]:
    calls = await store.list_calls(user_id)
    names = {c["phone_e164"]: c["name"] for c in await store.list_contacts(user_id)}
    keep = (
        "id",
        "other_number",
        "call_lang",
        "status",
        "kind",
        "created_at",
        "duration_s",
        "provider",
    )
    return [
        {**{k: c.get(k) for k in keep}, "name": names.get(c.get("other_number"))} for c in calls
    ]
