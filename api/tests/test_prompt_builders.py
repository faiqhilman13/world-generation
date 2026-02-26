import pytest

from app.services.prompt_builders import build_permission, build_world_prompt


def test_build_world_prompt_text():
    payload = build_world_prompt(
        prompt_type="text",
        source_media_asset_id=None,
        text_prompt="A Scandinavian living room",
    )
    assert payload == {"type": "text", "text_prompt": "A Scandinavian living room"}


def test_build_world_prompt_image():
    payload = build_world_prompt(
        prompt_type="image",
        source_media_asset_id="media_1",
        text_prompt=None,
    )
    assert payload == {
        "type": "image",
        "image_prompt": {
            "source": "media_asset",
            "media_asset_id": "media_1",
        },
    }


def test_build_world_prompt_image_with_options():
    payload = build_world_prompt(
        prompt_type="image",
        source_media_asset_id="media_1",
        text_prompt="Warm lighting",
        disable_recaption=True,
        is_pano=False,
    )
    assert payload == {
        "type": "image",
        "image_prompt": {
            "source": "media_asset",
            "media_asset_id": "media_1",
        },
        "text_prompt": "Warm lighting",
        "disable_recaption": True,
        "is_pano": False,
    }


def test_build_world_prompt_multi_image():
    payload = build_world_prompt(
        prompt_type="multi_image",
        source_media_asset_id="media_1",
        text_prompt=None,
    )
    assert payload == {
        "type": "multi-image",
        "multi_image_prompt": [
            {
                "content": {
                    "source": "media_asset",
                    "media_asset_id": "media_1",
                }
            }
        ],
    }


def test_build_world_prompt_multi_image_with_references_and_reconstruct():
    payload = build_world_prompt(
        prompt_type="multi_image",
        source_media_asset_id="base_room",
        text_prompt="Use walnut wood tones",
        reconstruct_images=True,
        reference_media_asset_ids=["ref_sofa", "ref_wallpaper"],
    )
    assert payload == {
        "type": "multi-image",
        "multi_image_prompt": [
            {
                "content": {
                    "source": "media_asset",
                    "media_asset_id": "base_room",
                }
            },
            {
                "content": {
                    "source": "media_asset",
                    "media_asset_id": "ref_sofa",
                }
            },
            {
                "content": {
                    "source": "media_asset",
                    "media_asset_id": "ref_wallpaper",
                }
            },
        ],
        "text_prompt": "Use walnut wood tones",
        "reconstruct_images": True,
    }


def test_build_world_prompt_requires_text():
    with pytest.raises(ValueError):
        build_world_prompt(
            prompt_type="text",
            source_media_asset_id=None,
            text_prompt=None,
        )


def test_build_world_prompt_requires_source_for_image():
    with pytest.raises(ValueError):
        build_world_prompt(
            prompt_type="image",
            source_media_asset_id=None,
            text_prompt=None,
        )


def test_build_world_prompt_multi_image_with_reference_only():
    payload = build_world_prompt(
        prompt_type="multi_image",
        source_media_asset_id=None,
        text_prompt=None,
        reference_media_asset_ids=["ref_1", "ref_2"],
    )
    assert payload == {
        "type": "multi-image",
        "multi_image_prompt": [
            {
                "content": {
                    "source": "media_asset",
                    "media_asset_id": "ref_1",
                }
            },
            {
                "content": {
                    "source": "media_asset",
                    "media_asset_id": "ref_2",
                }
            },
        ],
    }


def test_build_permission_defaults():
    assert build_permission(public=False) == {
        "public": False,
        "allowed_readers": [],
        "allowed_writers": [],
    }
