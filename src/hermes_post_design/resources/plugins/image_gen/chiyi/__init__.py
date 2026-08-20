"""Register the Chiyi image generation backend."""
from .provider import ChiyiImageGenProvider


def register(ctx) -> None:
    ctx.register_image_gen_provider(ChiyiImageGenProvider())
