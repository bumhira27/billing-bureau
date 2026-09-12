import time
from .base import BasePortalBot, RpaResult
from .simulator_bot import SimulatorPortalBot

class MedschemePortalBot(BasePortalBot):
    """
    RPA bot for Medscheme Provider Portal (GEMS, Bonitas, Polmed).
    Bypasses MediSwitch by submitting claims directly to Medscheme's portal.
    """
    DEFAULT_URL = "https://www.medscheme.co.za/provider"

    def verify_login(self) -> bool:
        return bool(self.username and self.password)

    def submit_claim(self, claim_dict: dict) -> RpaResult:
        claim_dict['scheme_name'] = 'Medscheme / GEMS Gateway'
        sim = SimulatorPortalBot(self.username, self.password, portal_url=self.portal_url or self.DEFAULT_URL, headless=self.headless)
        return sim.submit_claim(claim_dict)
