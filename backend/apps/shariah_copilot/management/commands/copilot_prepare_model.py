"""
Downloads the multilingual embedding model into COPILOT_MODEL_CACHE_DIR and checks that it works, so the first upload on a
server does not stall for minutes. Run it once at deployment (the Dockerfile does).

    python manage.py copilot_prepare_model
"""

from django.core.management.base import BaseCommand, CommandError

from apps.shariah_copilot import embeddings


class Command(BaseCommand):
    help = "Download and test the Shariah copilot's embedding model."

    def handle(self, *args, **options):
        if embeddings.backend() != "fastembed":
            self.stdout.write(f"Embedding backend is '{embeddings.backend()}': nothing to download.")
            return
        try:
            vectors = embeddings.embed(["late payment fee", "تاخیر سے ادائیگی پر جرمانہ"])
        except embeddings.EmbeddingsUnavailable as exc:
            raise CommandError(f"The embedding model could not be loaded: {exc}") from exc
        similarity = float(vectors[0] @ vectors[1])
        self.stdout.write(self.style.SUCCESS(
            f"Model ready: {embeddings.model_name()} ({vectors.shape[1]} dimensions). "
            f"English-Urdu similarity of a matching pair: {similarity:.2f}."
        ))
