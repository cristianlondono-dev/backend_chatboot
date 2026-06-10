# app/core/database/models.py

from app.modules.organizations.models import organization_model  # noqa
from app.modules.knowledge_bases.models import knowledge_base_model  # noqa
from app.modules.documents.models import document_model  # noqa
from app.modules.documents.models import document_chunk_model  # noqa
from app.modules.embeddings.models import chunk_embedding_model  # noqa
from app.modules.agents.models import agent_model  # noqa
from app.modules.agents.models import agent_knowledge_base_model  # noqa