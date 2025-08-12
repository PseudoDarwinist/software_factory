# IRR domain knowledge

- Cancellation events should use the IRR cancellation templates for clarity and compliance.
- Delay events often require concise SMS messaging; when delay is overnight and ≥ 4 hours, include hotel voucher guidance.
- Rebooking messages should clearly present new itinerary details; prefer email + SMS together for high-impact disruptions.
- Scheduled change communications should avoid alarming language and include self-service re-accommodation links where available.

```yaml rule
id: "EU261.Contextual.Guidance"
applies_when:
  event.type: "Delay"
  event.attrs.overnight: true
expect:
  actions_include: ["IssueHotelVoucher"]
```
