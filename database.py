import asyncio
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, Text, select, update, delete
import aiosqlite

# Database setup
DATABASE_URL = "sqlite+aiosqlite:///./linkedin_tokens.db"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession)

class Base(DeclarativeBase):
    pass

class LinkedInToken(Base):
    __tablename__ = "linkedin_tokens"
    
    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_type: Mapped[str] = mapped_column(String(50), default="Bearer")
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    scope: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

async def init_database():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def store_token(user_id: str, token_data: Dict[str, Any], email: Optional[str] = None) -> LinkedInToken:
    """Store or update LinkedIn token for a user"""
    async with async_session() as session:
        # Calculate expires_at if expires_in is provided
        expires_at = None
        if "expires_in" in token_data:
            expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
        
        # Check if token already exists
        stmt = select(LinkedInToken).where(LinkedInToken.user_id == user_id)
        result = await session.execute(stmt)
        existing_token = result.scalar_one_or_none()
        
        if existing_token:
            # Update existing token
            update_stmt = update(LinkedInToken).where(
                LinkedInToken.user_id == user_id
            ).values(
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                token_type=token_data.get("token_type", "Bearer"),
                expires_at=expires_at,
                scope=token_data.get("scope"),
                email=email,
                updated_at=datetime.utcnow()
            )
            await session.execute(update_stmt)
            await session.commit()
            
            # Fetch updated token
            result = await session.execute(stmt)
            return result.scalar_one()
        else:
            # Create new token
            new_token = LinkedInToken(
                user_id=user_id,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                token_type=token_data.get("token_type", "Bearer"),
                expires_at=expires_at,
                scope=token_data.get("scope"),
                email=email
            )
            session.add(new_token)
            await session.commit()
            await session.refresh(new_token)
            return new_token

async def get_token(user_id: str) -> Optional[LinkedInToken]:
    """Retrieve LinkedIn token for a user"""
    async with async_session() as session:
        stmt = select(LinkedInToken).where(LinkedInToken.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

async def get_valid_token(user_id: str) -> Optional[LinkedInToken]:
    """Get token only if it's still valid (not expired)"""
    token = await get_token(user_id)
    if not token:
        return None
    
    # Check if token is expired
    if token.expires_at and token.expires_at <= datetime.utcnow():
        return None
    
    return token

async def delete_token(user_id: str) -> bool:
    """Delete LinkedIn token for a user"""
    async with async_session() as session:
        stmt = delete(LinkedInToken).where(LinkedInToken.user_id == user_id)
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount > 0

async def list_all_tokens() -> list[LinkedInToken]:
    """List all stored tokens"""
    async with async_session() as session:
        stmt = select(LinkedInToken)
        result = await session.execute(stmt)
        return list(result.scalars().all())

async def cleanup_expired_tokens() -> int:
    """Remove expired tokens from database"""
    async with async_session() as session:
        stmt = delete(LinkedInToken).where(
            LinkedInToken.expires_at <= datetime.utcnow()
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount