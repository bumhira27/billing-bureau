from .base_bot import BasePortalBot, BotResult
from .simulator_bot import SimulatorPortalBot
from .dtos import ClaimDTO

class MedschemePortalBot(BasePortalBot):
    """
    RPA bot for Medscheme Provider Portal (GEMS, Bonitas, Polmed).
    Bypasses MediSwitch by submitting claims directly to Medscheme's portal.
    """
    DEFAULT_URL = "https://www.medscheme.co.za/provider"

    def submit_claim(self, claim_dto: ClaimDTO) -> BotResult:
        claim_dto.patient.scheme_name = 'Medscheme / GEMS Gateway'
        
        sim = SimulatorPortalBot(
            username=self.username, 
            password=self.password, 
            portal_url=self.portal_url or self.DEFAULT_URL, 
            headless=self.headless
        )
        return sim.submit_claim(claim_dto)
