import abc
from typing import Optional
from dataclasses import dataclass
from .dtos import ClaimDTO

@dataclass
class BotResult:
    success: bool
    message: str
    reference_number: str
    execution_time: float
    screenshot_bytes: Optional[bytes] = None

class BasePortalBot(abc.ABC):
    """
    Standard interface for all RPA bots communicating with medical aid portals.
    """
    def __init__(self, username: str, password: str, portal_url: str, headless: bool = True, dry_run: bool = True):
        self.username = username
        self.password = password
        self.portal_url = portal_url
        self.headless = headless
        self.dry_run = dry_run

    @abc.abstractmethod
    def submit_claim(self, claim_dto: ClaimDTO) -> BotResult:
        """
        Submit a single claim to the portal using the standard ClaimDTO.
        """
        pass
        
    @abc.abstractmethod
    def fetch_remittances(self, date_from: str, date_to: str) -> list[bytes]:
        """
        Download remittance advice files (eRA) from the portal for a given date range.
        Returns a list of file contents as bytes.
        """
        pass

    def verify_login(self) -> bool:
        """Verify that credentials are valid (default implementation)."""
        return bool(self.username and self.password)
