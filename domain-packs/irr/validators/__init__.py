from .custom import validate_channel_template_alignment, validate_sms_market_prefix, validate_icoupon_amount, validate_consent, validate_sandbox_whitelist, validate_locale_template_alignment, validate_duplicate_recipient

VALIDATORS = {
    "Consent": validate_consent,
    "SandboxWhitelist": validate_sandbox_whitelist,
    "LocaleTemplateAlignment": validate_locale_template_alignment,
    "DuplicateRecipient": validate_duplicate_recipient,
    "ICouponAmount": validate_icoupon_amount,
    "SMSMarketPrefix": validate_sms_market_prefix,
    "ChannelTemplateAlignment": validate_channel_template_alignment
}
from .custom import validate_eligibility
VALIDATORS["Eligibility"] = validate_eligibility
