# Network Hardening Plan (From Quick Fix to Enterprise)

## Phase 0 - Immediate Recovery (Now)
- Run `bash ops/network_fix.sh`
- Purpose: quickly unblock Cosmos firewall for current app egress.

## Phase 1 - Stable Egress IP (Low-to-Medium Effort)
Goal: keep app outbound IP stable so Cosmos firewall does not break randomly.

High-level steps:
1. Move/attach Container Apps environment to VNet-injected setup.
2. Add NAT Gateway on outbound subnet.
3. Use NAT public IP as the only Cosmos allowed IP.
4. Remove temporary IP rules added during incident recovery.

Result:
- Predictable egress IP
- Firewall rules become stable and auditable

## Phase 2 - Private Endpoint (Enterprise Target)
Goal: remove public path between app and Cosmos entirely.

High-level steps:
1. Create Cosmos DB Private Endpoint in same VNet.
2. Configure private DNS zone links.
3. Ensure app subnet can resolve Cosmos private endpoint.
4. Disable Cosmos public network access (or keep deny by default).

Result:
- App <-> Cosmos traffic stays on Azure private network
- Strongest network posture

## Recommended Order
1. Phase 0 now (minutes)
2. Phase 1 next (hours, planned window)
3. Phase 2 final (project hardening milestone)
