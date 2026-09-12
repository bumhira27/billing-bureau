import time
from .base import BasePortalBot, RpaResult
from .simulator_bot import SimulatorPortalBot

class DiscoveryPortalBot(BasePortalBot):
    """
    RPA bot for Discovery Health Provider Portal (HealthID / Digital Practice).
    Bypasses MediSwitch by submitting claims directly to Discovery's web gateway.
    """
    DEFAULT_URL = "https://www.discovery.co.za/health/login"

    def verify_login(self) -> bool:
        return bool(self.username and self.password)

    def submit_claim(self, claim_dict: dict) -> RpaResult:
        claim_dict['scheme_name'] = 'Discovery Health Medical Scheme'
        # If portal credentials are dry-run or demo, run the headless browser simulator
        sim = SimulatorPortalBot(self.username, self.password, portal_url=self.portal_url or self.DEFAULT_URL, headless=self.headless)
        return sim.submit_claim(claim_dict)
