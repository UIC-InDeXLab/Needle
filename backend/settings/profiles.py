"""Embedder profiles for the onboarding flow.

Each profile trades accuracy for speed/resource use by loading a different number
of image embedders. These are the source of truth used by the setup flow to write
the active ``embedders.json`` into the (writable) app data directory.
"""

PROFILES = {
    "fast": {
        "label": "Fast",
        "description": "1–2 lightweight models. Fastest indexing and search, lowest memory.",
        "image_embedders": [
            {"name": "regnet", "model_name": "regnety_1280.swag_ft_in1k", "weight": 0.5},
            {"name": "eva", "model_name": "eva02_large_patch14_448.mim_m38m_ft_in22k_in1k", "weight": 0.5},
        ],
    },
    "balanced": {
        "label": "Balanced",
        "description": "4 models. Good balance of accuracy and resource use.",
        "image_embedders": [
            {"name": "dino", "model_name": "vit_large_patch14_reg4_dinov2.lvd142m", "weight": 0.25},
            {"name": "convnextv2", "model_name": "convnextv2_large.fcmae_ft_in22k_in1k_384", "weight": 0.25},
            {"name": "clip", "model_name": "vit_base_patch16_clip_224.openai", "weight": 0.25},
            {"name": "eva", "model_name": "eva02_large_patch14_448.mim_m38m_ft_in22k_in1k", "weight": 0.25},
        ],
    },
    "accurate": {
        "label": "Accurate",
        "description": "6 models. Highest accuracy; needs the most memory and time.",
        "image_embedders": [
            {"name": "eva", "model_name": "eva02_large_patch14_448.mim_m38m_ft_in22k_in1k", "weight": 0.8497},
            {"name": "regnet", "model_name": "regnety_1280.swag_ft_in1k", "weight": 0.8235},
            {"name": "dino", "model_name": "vit_large_patch14_reg4_dinov2.lvd142m", "weight": 0.8235},
            {"name": "clip", "model_name": "vit_large_patch14_clip_336.openai_ft_in12k_in1k", "weight": 0.8146},
            {"name": "convnextv2", "model_name": "convnextv2_large.fcmae_ft_in22k_in1k_384", "weight": 0.8184},
            {"name": "bevit", "model_name": "beitv2_large_patch16_224.in1k_ft_in22k_in1k", "weight": 0.7660},
        ],
    },
}

DEFAULT_PROFILE = "fast"


def profile_options():
    """Return lightweight metadata for the UI (no heavy model loading)."""
    return [
        {
            "id": key,
            "label": prof["label"],
            "description": prof["description"],
            "num_models": len(prof["image_embedders"]),
        }
        for key, prof in PROFILES.items()
    ]


def get_profile(profile_id: str):
    if profile_id not in PROFILES:
        raise ValueError(f"Unknown profile '{profile_id}'")
    return PROFILES[profile_id]
