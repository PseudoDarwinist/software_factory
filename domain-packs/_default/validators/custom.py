from typing import List, Dict, Any

def validate_channel_template_alignment(log: Dict[str, Any]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    event = log.get("event", {})
    decision = log.get("decision", {})
    channel = decision.get("channel")
    template_id = decision.get("template_id")
    event_type = event.get("type")
    # SMS for rebook/delay must use SMS templates (irr_*_sms_*) to fit character limits
    if channel == "SMS" and template_id and template_id.endswith("_email_01"):
        findings.append({
            "kind": "Tpl.Select",
            "severity": "med",
            "details": {
                "message": "SMS channel must use SMS templates to fit character limits",
                "channel": channel,
                "template_id": template_id,
                "event_type": event_type
            },
            "suggested_fix": "Use irr_*_sms_* template variants for SMS channel"
        })
    return findings


from pathlib import Path
import json

def validate_sms_market_prefix(log):
    findings = []
    decision = log.get('decision', {})
    event = log.get('event', {})
    if decision.get('channel') != 'SMS':
        return findings
    prefix = (event.get('attrs') or {}).get('phone_e164_prefix')
    try:
        allowed = json.loads(Path(__file__).resolve().parents[1].joinpath('mappings/allowed_prefixes.json').read_text())['allowed_prefixes']
    except Exception:
        allowed = []
    if prefix and prefix not in allowed:
        findings.append({
            'kind': 'Delivery.Blocked',
            'severity': 'high',
            'details': {
                'message': 'SMS not allowed for market prefix',
                'prefix': prefix
            },
            'suggested_fix': 'Suppress SMS or use allowed channel for this market'
        })
    return findings



def _load_icoupon_rules():
    try:
        data = json.loads(Path(__file__).resolve().parents[1].joinpath('mappings/icoupon_voucher_rules.json').read_text())['rules']
        # index by (airport, class_code) and delay range
        indexed = {}
        for r in data:
            key = (r.get('airport'), r.get('class_code'))
            indexed.setdefault(key, []).append(r)
        # sort each list by min_delay_min ascending
        for k in indexed:
            indexed[k].sort(key=lambda x: (x.get('min_delay_min') or 0))
        return indexed
    except Exception:
        return {}

_IC_RULES = _load_icoupon_rules()


def validate_icoupon_amount(log):
    findings = []
    event = log.get('event', {})
    decision = log.get('decision', {})
    attrs = event.get('attrs') or {}
    if event.get('type') != 'Delay':
        return findings
    if not decision.get('action') or 'coupon' not in decision.get('action', '').lower():
        return findings
    airport = attrs.get('origin') or attrs.get('airport')
    class_code = attrs.get('service_class') or attrs.get('booking_class')
    delay_min = attrs.get('delay_minutes')
    amount = decision.get('voucher_amount')
    currency = decision.get('voucher_currency')
    if not (airport and class_code and isinstance(delay_min, (int, float)) and amount and currency):
        return findings
    candidates = _IC_RULES.get((airport, class_code)) or []
    match = None
    for r in candidates:
        mn = r.get('min_delay_min') or 0
        mx = r.get('max_delay_min') or 10**9
        if delay_min >= mn and delay_min <= mx:
            match = r
            break
    if not match:
        findings.append({
            'kind': 'Policy.Misapplied',
            'severity': 'high',
            'details': {
                'message': 'No voucher rule matched for airport/class/delay',
                'airport': airport,
                'class_code': class_code,
                'delay_minutes': delay_min
            },
            'suggested_fix': 'Add or correct IRR_Icoupon_Voucher metadata for this case'
        })
        return findings
    # compare amount and currency
    expected_amt = match.get('amount')
    expected_ccy = match.get('currency')
    if currency != expected_ccy or abs(float(amount) - float(expected_amt)) > 0.01:
        findings.append({
            'kind': 'Policy.Misapplied',
            'severity': 'high',
            'details': {
                'message': 'Voucher amount/currency mismatch',
                'expected_amount': expected_amt,
                'expected_currency': expected_ccy,
                'actual_amount': amount,
                'actual_currency': currency,
                'airport': airport,
                'class_code': class_code,
                'delay_minutes': delay_min
            },
            'suggested_fix': 'Use configured voucher value for airport/class/delay window'
        })
    return findings


import hashlib


def validate_consent(log):
    findings = []
    event = log.get('event', {})
    decision = log.get('decision', {})
    consent = (event.get('attrs') or {}).get('gdpr_consent')
    if decision.get('status') == 'SKIPPED':
        return findings
    if consent is False or consent in (None, ''):
        findings.append({
            'kind': 'Consent.Missing',
            'severity': 'high',
            'details': {'message': 'GDPR consent missing or false'},
            'suggested_fix': 'Obtain/record consent before sending'
        })
    return findings


def validate_sandbox_whitelist(log):
    findings = []
    event = log.get('event', {})
    decision = log.get('decision', {})
    env = (event.get('attrs') or {}).get('environment')
    if env != 'SANDBOX':
        return findings
    recipient = (event.get('attrs') or {}).get('recipient') or decision.get('recipient')
    try:
        wl = json.loads(Path(__file__).resolve().parents[1].joinpath('mappings/recipient_whitelist.json').read_text())['whitelist']
    except Exception:
        wl = []
    if recipient and recipient not in wl:
        findings.append({
            'kind': 'Delivery.WhitelistedSandbox',
            'severity': 'high',
            'details': {'recipient': recipient},
            'suggested_fix': 'Add to whitelist or suppress sends in sandbox'
        })
    return findings


def validate_locale_template_alignment(log):
    findings = []
    event = log.get('event', {})
    decision = log.get('decision', {})
    market = (event.get('attrs') or {}).get('market')
    template_id = decision.get('template_id') or ''
    if not market or not template_id:
        return findings
    # heuristic: US templates contain _US; Swedish market SV should not use _US
    if market == 'US' and '_US' not in template_id:
        findings.append({'kind': 'Content.LocaleMismatch','severity': 'med','details': {'market': market, 'template_id': template_id}, 'suggested_fix': 'Use US variant template'})
    if market in ('SE','SV','Sweden') and '_US' in template_id:
        findings.append({'kind': 'Content.LocaleMismatch','severity': 'med','details': {'market': market, 'template_id': template_id}, 'suggested_fix': 'Use localized template for market'})
    return findings

_DUP_CACHE = {}

def validate_duplicate_recipient(log):
    findings = []
    event = log.get('event', {})
    decision = log.get('decision', {})
    ts = event.get('ts')
    recipient = (event.get('attrs') or {}).get('recipient') or decision.get('recipient')
    msg_type = decision.get('action')
    if not (ts and recipient and msg_type):
        return findings
    key = hashlib.sha256(f"{recipient}|{msg_type}".encode()).hexdigest()
    # simple in-memory, replace with store in production
    if key in _DUP_CACHE:
        findings.append({'kind': 'Audience.Duplicate','severity': 'med','details': {'recipient': recipient, 'action': msg_type}, 'suggested_fix': 'Suppress duplicate within window'})
    _DUP_CACHE[key] = ts
    return findings

import yaml

def _load_yaml_mapping(rel):
    try:
        import yaml
        from pathlib import Path
        p = Path(__file__).resolve().parents[1].joinpath(rel)
        return yaml.safe_load(p.read_text())
    except Exception:
        return {}

_ELIG = _load_yaml_mapping('mappings/eligibility.yaml') or {}


def _eval_predicate(log, pred):
    from operator import eq, ne
    ops = {
        '==': lambda a,b: a == b,
        '!=': lambda a,b: a != b,
        '<': lambda a,b: a is not None and b is not None and a < b,
        '<=': lambda a,b: a is not None and b is not None and a <= b,
        '>': lambda a,b: a is not None and b is not None and a > b,
        '>=': lambda a,b: a is not None and b is not None and a >= b,
        'in': lambda a,b: a in (b or []),
    }
    def get(path):
        cur = {'event': log.get('event', {}), 'decision': log.get('decision', {})}
        for part in path.split('.'):
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                return None
        return cur
    left = get(pred.get('left')) if pred.get('left') else None
    right = pred.get('right')
    if pred.get('right_mapping'):
        m = _ELIG.get('Lists', {}).get(pred['right_mapping'], [])
        right = m
    op = ops.get(pred.get('op'))
    return bool(op(left, right)) if op else False


def validate_eligibility(log):
    findings = []
    event_type = (log.get('event') or {}).get('type')
    attrs = (log.get('event') or {}).get('attrs') or {}
    rules = (_ELIG.get('eligibility') or {}).get(event_type) or []
    # Common rules (like US station list)
    common_any = (_ELIG.get('eligibility') or {}).get('Common') or []
    # Evaluate rule structures
    def add(kind, msg):
        findings.append({'kind': kind, 'severity': 'high', 'details': {'message': msg}})
    for rule in rules:
        if 'when' in rule:
            if not _eval_predicate(log, rule['when']):
                add('Eligibility.TimeWindow', f"Rule {rule['id']} not satisfied")
        if 'when_all' in rule:
            if not all(_eval_predicate(log, p) for p in rule['when_all']):
                add('Eligibility.TimeWindow', f"Rule {rule['id']} not satisfied")
        if 'bands' in rule:
            dd = attrs.get('delayDifference')
            boarded = attrs.get('hasBoarded')
            ok = False
            for band in rule['bands']:
                minv = band.get('min')
                maxv = band.get('max')
                in_band = True
                if minv is not None and (dd is None or dd < minv):
                    in_band = False
                if maxv is not None and (dd is None or dd >= maxv):
                    in_band = False
                if not in_band:
                    continue
                reqs = band.get('require') or []
                if all(_eval_predicate(log, r) for r in reqs):
                    ok = True
                    break
            if not ok:
                add('Eligibility.BoardingState', 'Delay band requirements not met')
    for rule in common_any:
        if 'when_any' in rule:
            if not any(_eval_predicate(log, p) for p in rule['when_any']):
                add('Eligibility.MarketRoute', f"Common rule {rule['id']} not satisfied")
    return findings
