# TTN replay fixtures

`outflow-a-redacted.json` is a small privacy-redacted derivative of the local
TTN Live Data console export. It keeps one normal decoded uplink, one uplink
with a status block, and one non-uplink event using the source structures and
values. All external device, application, gateway, session, correlation, and
network identifiers are stable synthetic replacements.

The invalid decoded uplink is an explicit test-only mutation of the normal
uplink because the source export contains no invalid `as.up.data.forward`
event. Its decoded payload is marked `valid: false` with `err: 1`; it is not
presented as captured device evidence.

The full `outflow-a-live-data.json` export and the reference
`outflow-a-decoder.js` remain exact, read-only, ignored local files. They must
not be staged or committed.
