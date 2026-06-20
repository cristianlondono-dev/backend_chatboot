import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agents.models.agent_model import Agent
from app.modules.escalations.models.escalation_model import Escalation
from app.modules.memory.models.chat_session_model import ChatSession
from app.modules.memory.models.user_channel_model import UserChannel
from app.modules.organizations.models.organization_model import Organization


class EscalationRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        tool_action_id: uuid.UUID | None,
        summary: str
    ) -> Escalation:
        obj = Escalation(
            agent_id=agent_id,
            user_id=user_id,
            session_id=session_id,
            tool_action_id=tool_action_id,
            summary=summary,
        )
        self.db.add(obj)
        await self.db.commit()
        await self.db.refresh(obj)
        return obj

    async def list_all(self, is_resolved: bool | None = None) -> list[dict]:
        query = (
            select(Escalation, Agent.name, Organization.trade_name)
            .join(Agent, Agent.id == Escalation.agent_id)
            .join(Organization, Organization.id == Agent.organization_id)
            .order_by(Escalation.created_at.desc())
        )
        if is_resolved is not None:
            query = query.where(Escalation.is_resolved == is_resolved)

        rows = (await self.db.execute(query)).all()
        if not rows:
            return []

        user_ids = {row[0].user_id for row in rows}
        channels_result = await self.db.execute(
            select(UserChannel).where(UserChannel.user_id.in_(user_ids))
        )
        channel_by_user: dict[uuid.UUID, UserChannel] = {}
        for channel in channels_result.scalars().all():
            channel_by_user.setdefault(channel.user_id, channel)

        out = []
        for escalation, agent_name, organization_name in rows:
            channel = channel_by_user.get(escalation.user_id)
            out.append({
                "id": escalation.id,
                "agent_id": escalation.agent_id,
                "agent_name": agent_name,
                "organization_name": organization_name,
                "channel": channel.channel if channel else None,
                "channel_id": channel.channel_id if channel else None,
                "summary": escalation.summary,
                "is_resolved": escalation.is_resolved,
                "created_at": escalation.created_at,
                "resolved_at": escalation.resolved_at,
            })
        return out

    async def get_detail(self, escalation_id: uuid.UUID) -> dict | None:
        query = (
            select(Escalation, Agent.name, Organization.trade_name, ChatSession.is_paused)
            .join(Agent, Agent.id == Escalation.agent_id)
            .join(Organization, Organization.id == Agent.organization_id)
            .join(ChatSession, ChatSession.id == Escalation.session_id)
            .where(Escalation.id == escalation_id)
        )
        row = (await self.db.execute(query)).first()
        if not row:
            return None
        escalation, agent_name, organization_name, is_paused = row

        channel_result = await self.db.execute(
            select(UserChannel).where(UserChannel.user_id == escalation.user_id)
        )
        channel = channel_result.scalars().first()

        return {
            "id": escalation.id,
            "agent_id": escalation.agent_id,
            "agent_name": agent_name,
            "organization_name": organization_name,
            "user_id": escalation.user_id,
            "session_id": escalation.session_id,
            "channel": channel.channel if channel else None,
            "channel_id": channel.channel_id if channel else None,
            "summary": escalation.summary,
            "is_resolved": escalation.is_resolved,
            "is_paused": is_paused,
            "created_at": escalation.created_at,
            "resolved_at": escalation.resolved_at,
        }

    async def set_resolved(self, escalation_id: uuid.UUID, is_resolved: bool) -> Escalation | None:
        result = await self.db.execute(select(Escalation).where(Escalation.id == escalation_id))
        record = result.scalar_one_or_none()
        if not record:
            return None

        record.is_resolved = is_resolved
        record.resolved_at = datetime.now(timezone.utc) if is_resolved else None
        await self.db.commit()
        await self.db.refresh(record)

        if is_resolved:
            # Un escalamiento resuelto siempre implica que el bot debe volver
            # a responder en esa conversación.
            await self.db.execute(
                update(ChatSession)
                .where(ChatSession.id == record.session_id)
                .values(is_paused=False)
            )
            await self.db.commit()

        return record
