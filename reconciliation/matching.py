from datetime import timedelta
from decimal import Decimal
from django.db import transaction
from django.db.models import Q
from .models import ReconciliationLog
from claims.models import ClaimLineItem


class AutoMatcher:
    def __init__(self):
        pass

    def match_remittance_file(self, remittance_file):
        summary = {'matched': 0, 'unmatched': 0, 'errors': 0}
        affected_claims = set()

        for line in remittance_file.lines.all():
            with transaction.atomic():
                # 1. First attempt: Match by exact switch/invoice reference if available on line or membership
                matches = ClaimLineItem.objects.none()
                if line.membership_number and '/' in line.membership_number:
                    matches = ClaimLineItem.objects.filter(
                        claim__switch_reference_number__icontains=line.membership_number,
                        tariff_code=line.tariff_code
                    )

                # 2. Second attempt: Match by BHF + scheme membership + date + tariff
                if not matches.exists():
                    matches = ClaimLineItem.objects.filter(
                        claim__practice__bhf_practice_number=line.practice_number,
                        claim__patient_scheme__membership_number=line.membership_number,
                        claim__date_of_service=line.date_of_service,
                        tariff_code=line.tariff_code
                    )

                # 3. Third attempt: Match by patient last name + date + tariff
                if not matches.exists() and line.patient_name:
                    last_name = line.patient_name.replace('MR', '').replace('MS', '').replace('MRS', '').replace('DR', '').strip().split()[-1]
                    matches = ClaimLineItem.objects.filter(
                        claim__patient__last_name__icontains=last_name,
                        claim__date_of_service=line.date_of_service,
                        tariff_code=line.tariff_code
                    )

                if matches.count() == 1:
                    match_id = matches.first().id
                    match = ClaimLineItem.objects.select_for_update().get(id=match_id)
                    line.match_status = 'auto_matched'
                    line.matched_claim_line_item = match
                    line.save(update_fields=['match_status', 'matched_claim_line_item'])

                    # Update ClaimLineItem
                    match.amount_paid = line.amount_paid
                    match.amount_patient_liable = max(Decimal('0.00'), match.amount_billed - match.amount_paid - match.amount_scheme_discount)
                    if match.amount_paid == 0:
                        match.line_status = 'rejected'
                    elif match.amount_paid >= match.amount_billed:
                        match.line_status = 'paid'
                    else:
                        match.line_status = 'short_paid'

                    if line.reason_code:
                        match.rejection_code = line.reason_code
                    if line.reason_description:
                        match.rejection_description = line.reason_description
                    match.save()

                    ReconciliationLog.objects.create(
                        remittance_line=line,
                        claim_line_item=match,
                        match_method='auto_exact',
                        match_confidence=100
                    )
                    summary['matched'] += 1
                    affected_claims.add(match.claim)

                elif matches.count() == 0:
                    # Fuzzy match (+/- 3 days)
                    last_name = line.patient_name.replace('MR', '').replace('MS', '').replace('MRS', '').replace('DR', '').strip().split()[-1] if line.patient_name else ''
                    fuzzy_matches = ClaimLineItem.objects.filter(
                        Q(claim__patient__last_name__icontains=last_name) | Q(claim__patient_scheme__membership_number=line.membership_number),
                        tariff_code=line.tariff_code,
                        claim__date_of_service__gte=line.date_of_service - timedelta(days=3),
                        claim__date_of_service__lte=line.date_of_service + timedelta(days=3)
                    )
                    if fuzzy_matches.count() == 1:
                        match_id = fuzzy_matches.first().id
                        match = ClaimLineItem.objects.select_for_update().get(id=match_id)
                        line.match_status = 'auto_matched'
                        line.matched_claim_line_item = match
                        line.save(update_fields=['match_status', 'matched_claim_line_item'])

                        match.amount_paid = line.amount_paid
                        match.amount_patient_liable = max(Decimal('0.00'), match.amount_billed - match.amount_paid - match.amount_scheme_discount)
                        if match.amount_paid == 0:
                            match.line_status = 'rejected'
                        elif match.amount_paid >= match.amount_billed:
                            match.line_status = 'paid'
                        else:
                            match.line_status = 'short_paid'

                        if line.reason_code:
                            match.rejection_code = line.reason_code
                        if line.reason_description:
                            match.rejection_description = line.reason_description
                        match.save()

                        ReconciliationLog.objects.create(
                            remittance_line=line,
                            claim_line_item=match,
                            match_method='auto_fuzzy',
                            match_confidence=80
                        )
                        summary['matched'] += 1
                        affected_claims.add(match.claim)
                    else:
                        line.match_status = 'unmatched'
                        line.save(update_fields=['match_status'])
                        summary['unmatched'] += 1
                else:
                    line.match_status = 'unmatched'
                    line.save(update_fields=['match_status'])
                    summary['unmatched'] += 1

        with transaction.atomic():
            for claim in affected_claims:
                claim.recalculate_totals()

            remittance_file.records_matched = summary['matched']
            remittance_file.records_unmatched = summary['unmatched']
            remittance_file.processed_status = 'completed'
            remittance_file.save(update_fields=['records_matched', 'records_unmatched', 'processed_status'])

        return summary
