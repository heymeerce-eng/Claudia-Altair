"""
Gestión de perfiles de usuario.
Carga los perfiles desde variables de entorno con prefijo USER_N_.
"""
import os
from dataclasses import dataclass, field
from typing import Optional, Dict


@dataclass
class UserProfile:
    name: str
    whatsapp: str
    role: str
    instagram: Optional[str] = None
    target_program: Optional[str] = None   # "CRIBA" o "CEO"
    icloud_email: Optional[str] = None
    icloud_password: Optional[str] = None
    zoom_email: Optional[str] = None

    @property
    def first_name(self) -> str:
        return self.name.split()[0]

    def has_calendar(self) -> bool:
        pw = self.icloud_password or ""
        return bool(self.icloud_email and pw and pw != "xxxx-xxxx-xxxx-xxxx")

    def content_context(self) -> str:
        """Returns a brief context string for the agent system prompt."""
        parts = []
        if self.instagram:
            parts.append(f"Instagram: {self.instagram}")
        if self.target_program:
            persona = "Persona 1 (la que empieza / CRIBA)" if self.target_program == "CRIBA" \
                      else "Persona 2 (la que ya tiene negocio y quiere escalar / CEO)"
            parts.append(f"Su audiencia objetivo es: {persona}")
            parts.append(f"Programa que vende: {self.target_program}")
        return " · ".join(parts) if parts else ""


def load_profiles() -> Dict[str, UserProfile]:
    """Returns a dict keyed by WhatsApp number (e.g. 'whatsapp:+34600000000')."""
    profiles: Dict[str, UserProfile] = {}
    i = 1
    while True:
        name = os.environ.get(f"USER_{i}_NAME")
        if not name:
            break
        whatsapp = os.environ.get(f"USER_{i}_WHATSAPP", "").strip()
        if whatsapp:
            profiles[whatsapp] = UserProfile(
                name=name,
                whatsapp=whatsapp,
                role=os.environ.get(f"USER_{i}_ROLE", "Socia de ALTAIR"),
                instagram=os.environ.get(f"USER_{i}_INSTAGRAM"),
                target_program=os.environ.get(f"USER_{i}_TARGET_PROGRAM"),
                icloud_email=os.environ.get(f"USER_{i}_ICLOUD_EMAIL"),
                icloud_password=os.environ.get(f"USER_{i}_ICLOUD_PASSWORD"),
                zoom_email=os.environ.get(f"USER_{i}_ZOOM_EMAIL"),
            )
        i += 1
    return profiles


_PROFILES: Optional[Dict[str, UserProfile]] = None


def _normalize_whatsapp(number: str) -> str:
    """Returns 'whatsapp:+XXXXXXXXXXX' with no spaces."""
    n = number.strip().replace(" ", "").replace("-", "")
    if not n.startswith("whatsapp:"):
        n = "whatsapp:" + n
    return n.lower()


def get_profile(whatsapp_number: str) -> Optional[UserProfile]:
    global _PROFILES
    if _PROFILES is None:
        _PROFILES = load_profiles()
    # Exact match first
    if whatsapp_number in _PROFILES:
        return _PROFILES[whatsapp_number]
    # Normalized match (handles format differences from Twilio)
    normalized = _normalize_whatsapp(whatsapp_number)
    for key, profile in _PROFILES.items():
        if _normalize_whatsapp(key) == normalized:
            return profile
    return None


def get_all_profiles() -> Dict[str, UserProfile]:
    global _PROFILES
    if _PROFILES is None:
        _PROFILES = load_profiles()
    return _PROFILES
