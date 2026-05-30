"""Per-user session management for the ConnectLife MCP server."""

import asyncio
import logging
import os
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from connectlife.api import ConnectLifeApi, LifeConnectAuthError, LifeConnectError
from connectlife.appliance import ConnectLifeAppliance

_LOGGER = logging.getLogger(__name__)

SESSION_TTL_SECONDS: int = int(os.environ.get("CONNECTLIFE_SESSION_TTL", "86400"))
POLL_INTERVAL_SECONDS: int = int(os.environ.get("CONNECTLIFE_POLL_INTERVAL", "60"))
MAX_SESSIONS: int = int(os.environ.get("CONNECTLIFE_MAX_SESSIONS", "100"))
_DEFAULT_SESSION_ID: str = "__default__"


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


class SessionError(Exception):
    """Raised when a session is not found or has expired."""


@dataclass
class Session:
    """A single ConnectLife user session with background polling."""

    session_id: str
    username: str
    api: ConnectLifeApi = field(repr=False)
    appliances: dict[str, ConnectLifeAppliance] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utcnow)
    last_used: datetime = field(default_factory=_utcnow)
    poll_task: asyncio.Task | None = field(default=None, repr=False, compare=False)


class SessionManager:
    """Thread-safe, per-user ConnectLife session registry."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = asyncio.Lock()
        self._default_session_id: str | None = None
        self._default_credentials: tuple[str, str] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def init_default_session(self) -> None:
        """Create a default session from environment variables on startup."""
        username = os.environ.get("MCP_CONNECTLIFE_USERNAME")
        password = os.environ.get("MCP_CONNECTLIFE_PASSWORD")
        if not username or not password:
            return

        self._default_session_id = _DEFAULT_SESSION_ID
        self._default_credentials = (username, password)

        try:
            session = await self._relogin_default()
        except Exception:
            _LOGGER.exception("Failed to initialize default session")
            return

        if session.poll_task is None or session.poll_task.done():
            session.poll_task = asyncio.create_task(
                self._poll_loop(self._default_session_id),
                name="poll-default",
            )
        _LOGGER.info("Default session initialized")

    async def create(self, username: str, password: str) -> str:
        """Authenticate with ConnectLife and return a new session token.

        Raises:
            LifeConnectAuthError: Invalid username / password.
            ConnectionError: Transient API failure.
            RuntimeError: Server-side session limit exceeded.
        """
        async with self._lock:
            if len(self._sessions) >= MAX_SESSIONS:
                self._evict_expired_locked()
                if len(self._sessions) >= MAX_SESSIONS:
                    raise RuntimeError("Maximum concurrent sessions reached")

        api = await self._authenticate(username, password)
        session_id = secrets.token_urlsafe(32)
        session = Session(
            session_id=session_id,
            username=username,
            api=api,
            appliances={a.device_id: a for a in api.appliances},
        )
        session.poll_task = asyncio.create_task(
            self._poll_loop(session_id),
            name=f"poll-{session_id[:8]}",
        )

        async with self._lock:
            self._sessions[session_id] = session

        _LOGGER.info("Session created (id=…%s)", session_id[-8:])
        return session_id

    def get(self, session_id: str) -> Session:
        """Return the active session or raise SessionError."""
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionError("Session not found or expired")
        ttl = timedelta(seconds=SESSION_TTL_SECONDS)
        if _utcnow() - session.last_used > ttl:
            asyncio.create_task(self.remove(session_id))
            raise SessionError("Session has expired")
        session.last_used = _utcnow()
        return session

    async def resolve_session(self, session_id: str | None = None) -> Session:
        """Resolve session by id, or the default session if id is not provided.

        For the default session, automatically re-authenticates if expired or missing.
        """
        if session_id and session_id != self._default_session_id:
            return self.get(session_id)

        if self._default_session_id is None:
            raise SessionError("No session provided and no default session configured")

        session = self._sessions.get(self._default_session_id)
        ttl = timedelta(seconds=SESSION_TTL_SECONDS)

        if session is None or _utcnow() - session.last_used > ttl:
            session = await self._relogin_default()
            if session.poll_task is None or session.poll_task.done():
                session.poll_task = asyncio.create_task(
                    self._poll_loop(self._default_session_id),
                    name="poll-default",
                )

        session.last_used = _utcnow()
        return session

    async def remove(self, session_id: str) -> bool:
        """Cancel and remove a session. Returns True if the session existed."""
        async with self._lock:
            session = self._sessions.pop(session_id, None)
        if session is None:
            return False
        if session.poll_task and not session.poll_task.done():
            session.poll_task.cancel()
        _LOGGER.info("Session removed (id=…%s)", session_id[-8:])
        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evict_expired_locked(self) -> None:
        """Remove all expired sessions (must be called while holding self._lock)."""
        ttl = timedelta(seconds=SESSION_TTL_SECONDS)
        now = _utcnow()
        expired = [sid for sid, s in self._sessions.items() if now - s.last_used > ttl]
        for sid in expired:
            session = self._sessions.pop(sid, None)
            if session and session.poll_task and not session.poll_task.done():
                session.poll_task.cancel()
        if expired:
            _LOGGER.debug("Evicted %d expired session(s)", len(expired))

    async def _authenticate(self, username: str, password: str) -> ConnectLifeApi:
        """Authenticate with ConnectLife and return an API client."""
        api = ConnectLifeApi(username, password)
        try:
            if not await api.authenticate():
                raise LifeConnectAuthError("Authentication failed")
            await api.login()
            await api.get_appliances()
        except LifeConnectAuthError:
            raise
        except LifeConnectError as err:
            raise ConnectionError(f"ConnectLife API error: {err}") from err
        return api

    async def _relogin_default(self) -> Session:
        """Re-authenticate the default session and update it in-place."""
        if self._default_credentials is None:
            raise SessionError("Default session not configured")
        if self._default_session_id is None:
            raise SessionError("Default session not configured")

        username, password = self._default_credentials
        api = await self._authenticate(username, password)
        default_id = self._default_session_id

        async with self._lock:
            session = self._sessions.get(default_id)
            if session is None:
                session = Session(
                    session_id=default_id,
                    username=username,
                    api=api,
                    appliances={a.device_id: a for a in api.appliances},
                )
                self._sessions[default_id] = session
            else:
                session.api = api
                session.appliances = {a.device_id: a for a in api.appliances}
                session.last_used = _utcnow()

        _LOGGER.info("Default session re-authenticated")
        return session

    async def _poll_loop(self, session_id: str) -> None:
        """Background coroutine: refresh appliance state every POLL_INTERVAL_SECONDS."""
        ttl = timedelta(seconds=SESSION_TTL_SECONDS)
        is_default = session_id == self._default_session_id
        while True:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
            session = self._sessions.get(session_id)
            if session is None:
                if is_default and self._default_credentials is not None:
                    try:
                        await self._relogin_default()
                    except Exception:
                        _LOGGER.exception("Default session re-login during poll failed")
                    continue
                return
            if _utcnow() - session.last_used > ttl:
                if is_default:
                    try:
                        await self._relogin_default()
                    except Exception:
                        _LOGGER.exception("Default session TTL re-login failed")
                    continue
                await self.remove(session_id)
                return
            try:
                await session.api.get_appliances()
                session.appliances = {a.device_id: a for a in session.api.appliances}
                if is_default:
                    session.last_used = _utcnow()
            except LifeConnectAuthError:
                if is_default:
                    _LOGGER.warning("Default session auth expired during poll — re-authenticating")
                    try:
                        await self._relogin_default()
                    except Exception:
                        _LOGGER.exception("Default session re-login after auth error failed")
                    continue
                _LOGGER.warning(
                    "Session auth expired during poll (id=…%s) — removing", session_id[-8:]
                )
                await self.remove(session_id)
                return
            except Exception:
                _LOGGER.debug("Poll failed for session …%s", session_id[-8:], exc_info=True)
