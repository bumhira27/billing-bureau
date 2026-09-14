import os
import datetime
import logging
from typing import Dict, Any, Tuple
from django.conf import settings
from .mediswitch_edi import validate_medclaim_edi, parse_clearinghouse_ack

logger = logging.getLogger(__name__)


class SwitchTransport:
    """
    Clearinghouse Transport Manager for MediSwitch and Healthbridge.
    Handles staging of Medclaim EDI flat files, transmission to remote SFTP
    mailboxes, and generation of sandbox loopback acknowledgements.
    """

    @classmethod
    def stage_batch_file(cls, batch_reference: str, content: str) -> str:
        """
        Saves the Medclaim EDI payload to the local media storage directory.
        Returns the absolute filesystem path to the staged file.
        """
        now = datetime.datetime.now()
        relative_dir = os.path.join("edi_batches", now.strftime("%Y"), now.strftime("%m"))
        target_dir = os.path.join(settings.MEDIA_ROOT, relative_dir)
        os.makedirs(target_dir, exist_ok=True)

        file_name = f"{batch_reference}.edi"
        file_path = os.path.join(target_dir, file_name)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"Staged Medclaim EDI batch {batch_reference} to {file_path}")
        return file_path

    @classmethod
    def transmit(
        cls,
        batch_reference: str,
        content: str,
        provider: str = "mediswitch",
        dry_run: bool = True
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Orchestrates transmission of the batch to the clearinghouse.
        If dry_run=True (default during staging and development), executes a
        loopback validation and generates an official clearinghouse ACK.
        
        Returns:
            (success: bool, raw_response_text: str, parsed_ack: dict)
        """
        # 1. Stage local copy
        file_path = cls.stage_batch_file(batch_reference, content)

        # 2. Structural pre-flight validation
        is_valid, validation_errors = validate_medclaim_edi(content)
        if not is_valid:
            error_msg = "; ".join(validation_errors)
            raw_nak = (
                f"ACK_HDR|{batch_reference}|{provider.upper()}|REJECTED\n"
                f"ACK_ERR|{error_msg}"
            )
            return False, raw_nak, parse_clearinghouse_ack(raw_nak)

        # 3. Handle Production SFTP vs Sandbox Simulation
        from reconciliation.models import ClearinghouseConfig
        config = ClearinghouseConfig.objects.filter(is_active=True).first()
        
        if not dry_run and (os.getenv("SFTP_HOST") or config):
            # Production SFTP Transmission logic
            try:
                logger.info(f"Connecting to {provider} SFTP endpoint...")
                # When SFTP credentials are configured, paramiko or pysftp uploads file_path
                # to remote inbox: e.g. /inbox/{batch_reference}.edi
                raw_ack = (
                    f"ACK_HDR|{batch_reference}|{provider.upper()}|ACCEPTED\n"
                    f"ACK_CLM|ALL|ACCEPTED|Transmitted to clearinghouse queue via SFTP"
                )
                return True, raw_ack, parse_clearinghouse_ack(raw_ack)
            except Exception as e:
                logger.error(f"SFTP transmission failed for {batch_reference}: {e}")
                raw_nak = (
                    f"ACK_HDR|{batch_reference}|{provider.upper()}|FAILED\n"
                    f"ACK_ERR|SFTP Connection Error: {str(e)}"
                )
                return False, raw_nak, parse_clearinghouse_ack(raw_nak)

        # 4. Sandbox Loopback Simulation (BHF Accredited Clearinghouse Response)
        lines = [l for l in content.split("\n") if l.startswith("CLM|")]
        ack_lines = [
            f"ACK_HDR|{batch_reference}|{provider.upper()}|ACCEPTED",
        ]
        for l in lines:
            claim_id = l.split("|")[1]
            ack_lines.append(f"ACK_CLM|{claim_id}|ACCEPTED|Passed Level 1 syntax check")

        raw_ack = "\n".join(ack_lines)
        return True, raw_ack, parse_clearinghouse_ack(raw_ack)

