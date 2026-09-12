from .base_bot import BasePortalBot, BotResult
from .simulator_bot import SimulatorPortalBot
from .dtos import ClaimDTO

class DiscoveryPortalBot(BasePortalBot):
    """
    RPA bot for Discovery Health Provider Portal.
    Bypasses MediSwitch by submitting claims directly to Discovery's portal.
    """
    DEFAULT_URL = "https://www.discovery.co.za/portal/provider"

    def submit_claim(self, claim_dto: ClaimDTO) -> BotResult:
        claim_dto.patient.scheme_name = 'Discovery Health Medical Scheme'
        
        sim = SimulatorPortalBot(
            username=self.username, 
            password=self.password, 
            portal_url=self.portal_url or self.DEFAULT_URL, 
            headless=self.headless
        )
        return sim.submit_claim(claim_dto)
