import abc
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class RpaResult:
    success: bool
    reference_number: str
    message: str
    screenshot_bytes: Optional[bytes] = None
    execution_time: float = 0.0
    portal_name: str = ""

class BasePortalBot(abc.ABC):
    def __init__(self, username: str, password: str, portal_url: Optional[str] = None, headless: bool = True):
        self.username = username
        self.password = password
        self.portal_url = portal_url
        self.headless = headless

    @abc.abstractmethod
    def submit_claim(self, claim_dict: Dict[str, Any]) -> RpaResult:
        """
        Automates browser login, claim form input, and reads confirmation response.
        """
        pass

    @abc.abstractmethod
    def verify_login(self) -> bool:
        """
        Tests whether the provided credentials authenticate cleanly on the portal.
        """
        pass
