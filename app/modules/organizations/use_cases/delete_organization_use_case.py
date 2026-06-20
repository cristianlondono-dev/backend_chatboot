from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.core.logging.loggers import application_logger
from app.modules.agents.repositories.agent_repository import AgentRepository
from app.modules.knowledge_bases.repositories.knowledge_base_repository import (
    KnowledgeBaseRepository
)
from app.modules.knowledge_bases.use_cases.delete_knowledge_base_use_case import (
    DeleteKnowledgeBaseUseCase
)
from app.modules.memory.repositories.chat_session_repository import (
    ChatSessionRepository
)
from app.modules.memory.repositories.conversation_summary_repository import (
    ConversationSummaryRepository
)
from app.modules.memory.repositories.message_repository import MessageRepository
from app.modules.memory.repositories.user_memory_repository import (
    UserMemoryRepository
)
from app.modules.organizations.repositories.organization_repository import (
    OrganizationRepository
)


class DeleteOrganizationUseCase:
    """
    Deletes an organization and everything that hangs off it: agents (and
    their tools/tool actions, cascaded at the DB level), chat sessions,
    messages, user memories and conversation summaries for those agents, and
    every knowledge base (with its documents/chunks/embeddings).

    Users themselves are NOT deleted — they're cross-channel/cross-org
    identities (a phone number could also be talking to an agent in a
    different organization), only their data scoped to this org's agents is.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.org_repository = OrganizationRepository(db)
        self.agent_repository = AgentRepository(db)
        self.kb_repository = KnowledgeBaseRepository(db)
        self.chat_session_repository = ChatSessionRepository(db)
        self.message_repository = MessageRepository(db)
        self.user_memory_repository = UserMemoryRepository(db)
        self.conversation_summary_repository = ConversationSummaryRepository(db)

    async def execute(self, organization_id: UUID) -> None:
        org = await self.org_repository.get_by_id(organization_id)
        if not org:
            raise NotFoundException("Organización", str(organization_id))

        agents = await self.agent_repository.get_by_organization_id(organization_id)
        agent_ids = [agent.id for agent in agents]

        # Messages and summaries reference chat_sessions, so they must go
        # first. Order among memories/summaries doesn't matter (independent).
        await self.message_repository.delete_by_agent_ids(agent_ids)
        await self.conversation_summary_repository.delete_by_agent_ids(agent_ids)
        await self.user_memory_repository.delete_by_agent_ids(agent_ids)
        await self.chat_session_repository.delete_by_agent_ids(agent_ids)

        kbs = await self.kb_repository.get_by_organization_id(organization_id)
        for kb in kbs:
            await DeleteKnowledgeBaseUseCase(self.db).execute(kb.id)

        # Cascades at the DB level to agent_knowledge_bases, agent_tools and tool_actions.
        await self.agent_repository.delete_by_organization_id(organization_id)

        # Cascades at the DB level to organization_configs.
        await self.org_repository.delete(organization_id)
        await self.db.commit()

        application_logger.info(
            f"Organization deleted: '{org.trade_name}' | agents={len(agent_ids)} | kbs={len(kbs)} | id={org.id}"
        )
