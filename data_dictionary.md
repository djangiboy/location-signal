# Wiom Data Dictionary — Analytics-Relevant Tables

> **IST conversion**: `TO_DATE(DATEADD(minute, 330, <timestamp>))` and `CAST(DATEADD(minute, 330, <timestamp>) AS DATE)` are functionally equivalent. Use either.

## Core Transaction Tables

### t_router_user_mapping (PUBLIC)
**The most important table. Core transaction table for Home (first-pay) and Wiom Net recharges.**
- Each row = a device registration/recharge event
- **Key Columns**: transaction_id, mobile, router_nas_id, device_limit, otp, auth_state, store_group_id, charges, selected_plan_id, created_on, otp_issued_time, otp_expiry_time, created_by (partner), extra_data (JSON with totalPaid)
- store_group_id: 0 = regular Home plans, 1 = WiomNet (not required in Home filter — device_limit='10' is sufficient)
- **Home filter**: `device_limit='10' AND otp='DONE' AND mobile>'5999999999'`
- **Wiom Net filter**: `device_limit<'10' AND otp='DONE' AND mobile>'5999999999' AND store_group_id=1 AND charges<=100`
- **Active user filter**: `auth_state=1 AND otp NOT IN ('FREE','PAY_ONLINE','CASH','ROAM') AND mobile>'5999999999' AND charges>299`
- **Date for Home Transaction**: `TO_DATE(DATEADD(minute,330,created_on))`
- **Date for Wiom Net**: `TO_DATE(DATEADD(minute,330,otp_issued_time))`
- **Reports**: NSM, BDM, OKR1, OKR4a, OKR4b

### wiomBillingWifi (PUBLIC)
**Payment and billing records for WiFi recharges.**
- Matched to t_router_user_mapping by transaction_id or mobile (2-pass matching)
- **Key Columns**: transaction_id, mobile, total_price, paymentStatus, pay_ammount, payment_type, refund_status, createDate, BILL_ID, NASID
- **Valid payment filter**: `total_price>=299 AND paymentStatus=1 AND mobile>'5999999999' AND transaction_id NOT LIKE 'mr%' AND payment_type<>2 AND (refund_status<>1 OR refund_status IS NULL)`
- **VAS cxTeam filter**: `transaction_id ILIKE 'cxTeam%' AND paymentStatus=1`
- **Reports**: NSM, BDM, OKR1

### booking_logs (PUBLIC)
**Booking lifecycle events — creation, cancellation, refunds.**
- **Key Columns**: mobile, event_name, added_time, data (VARIANT/JSON with refund_amount)
- **New booking filter**: `event_name='booking_fee_captured'`
- **Cancellation filter**: `event_name IN ('cancelled','refund_initiated') AND TRY_TO_NUMBER(PARSE_JSON(data):refund_amount::STRING) > 0`
- **IST date**: `TO_DATE(DATEADD(minute,330,added_time))`
- **DATA JSON fields (booking_fee_captured)**: transaction_id (format: custGen_{mobile}_{id}_{suffix}), amount (₹100 standard, ₹25 historical — both valid)
- **DATA JSON fields (cancelled)**: initiated_by ('customer' or 'cops'=system), reason, refund_amount
- **DATA JSON fields (refund_initiated/refunded)**: reason, refund_amount
- **Booking lifecycle**: booking_fee_captured → [install funnel via TASK_LOGS] → OTP_VERIFIED (success) | cancelled | refund_initiated → refunded
- **Reports**: NSM, OKR1

### bookingvanilla_audit (PUBLIC)
**Installation payment and audit events.**
- **Key Columns**: mobile, event_name, paymentMode, added_time, KEY (= device_id)
- **Install payment filter**: `event_name='installation_fee_paid'`
- **Payment modes**: 'cash', 'offline', 'online'
- **Device ID**: `KEY` column = device_id
- **Reports**: NSM, OKR1

### PAYMENTVANILLA_AUDIT (PUBLIC)
**Payment audit/event log for customer payments.**
- **Key Columns**: mobile (VARCHAR — customer mobile), event_name (VARCHAR — payment event type), transaction_id (VARCHAR — payment transaction ID)
- **Reports**: OKR1

### TICKETVANILLA_AUDIT (PUBLIC)
**Ticket lifecycle audit events. Tracks status changes and actions on support tickets.**
- **Key Columns**: ticket_id (NUMBER — ticket ID), event_name (VARCHAR — ticket event type), added_time (TIMESTAMP — event timestamp), data (VARIANT — JSON event payload)
- **Reports**: OKR4a, CX

### TASK_LOGS (PUBLIC)
**End-to-end event log for booking → installation funnel. One row = one event.**
- **Key Columns**: MOBILE, ACCOUNT_ID (0=system, non-zero=partner), EVENT_NAME, DATA (VARIANT/JSON), ADDED_TIME (UTC)
- **Install complete**: `event_name = 'OTP_VERIFIED'`
- **Key events (chronological)**: GINIE_OUTPUT → NEW_LEAD_FPN_NOTIFICATION_SENT → NOTIF_SENT → INTERESTED → LATE_INTERESTED → SLOT_SELECTED → CUSTOMER_SLOT_CONFIRMED → DECLINED → ASSIGNED → REACHED_HOME → SELFIE → AADHAR → SHARED (₹300 deposit) → CONNECTION_INFO → DEVICE_PHOTO → SPEED_TEST → OTP_VERIFIED
- **INTERESTED vs LATE_INTERESTED**: Only the first partner to mark interest gets INTERESTED status and can assign a technician. All subsequent partners get LATE_INTERESTED.
- **Decline source**: `PARSE_JSON(DATA):source ILIKE '%system_force_declined%'` = system decline; else = manual partner decline
- **Router device ID from speed test**: `TRY_PARSE_JSON(data_json:extraData):deviceId::STRING`
- **Slot timestamps**: `selected_slot` inside DATA for SLOT_SELECTED and CUSTOMER_SLOT_CONFIRMED events is already in IST — do NOT apply +330 min offset
- **Mapping to booking**: Use booking window join (booking_verified_time to next_booking_verified_time), NOT a fixed 24-hour window
- **Reports**: OKR1, OKR2

### taskvanilla_audit (PUBLIC)
**Task/installation audit logs. Tracks partner installations and dispatch events.**
**Note**: Contains the same data as TASK_LOGS. Use either based on KPI definition context. TASK_LOGS is preferred for booking→install funnel analysis.
- **Key Columns**: mobile, event_name, added_time, account_id (partner account ID), KEY
- **Install filter**: `event_name='OTP_VERIFIED' AND mobile>'5999999999'`
- **Dispatch**: `event_name='NOTIF_SENT'` (sent to partner), `event_name='DECLINED'` (rejected)
- **Reports**: OKR1, OKR2

---

## Customer & Partner Tables

### t_wg_customer (PUBLIC, Fivetran)
**Customer-to-partner mapping. Maps device_id to NAS.**
- **Key Columns**: account_id, nasid, mobile, lco_account_id (partner), device_id, wiom_member, wg_status, added_time
- **Dedup**: ROW_NUMBER() OVER (PARTITION BY nasid ORDER BY added_time DESC) = 1
- **Reports**: NSM, BDM, OKR1, OKR4a, OKR4b

### HIERARCHY_BASE (PUBLIC)
**Partner hierarchy with geography mapping. Links partner account IDs to clusters/cities.**
**Use for geography/cluster mapping only.** For partner status and details, use supply_model.
- **Key Columns**: PARTNER_ACCOUNT_ID, cluster, MIS_CITY, ZONE, ZONE_DETAILED, DEDUP_FLAG, PARTNER_STATUS, PARTNER_NAME, PARTNER_MOBILE
- **ALWAYS filter**: `DEDUP_FLAG = 1`
- **City mapping**: `CASE WHEN cluster='Delhi' THEN 'Delhi' WHEN cluster='Mumbai' THEN 'Mumbai' ELSE 'Bharat' END`
- **Reports**: NSM, BDM, OKR1, OKR2, OKR4a, OKR4b

### partner_details_log (PUBLIC)
**Daily partner status snapshot. One full snapshot per day — ALWAYS filter to a single date.**
**Use for historical partner data at date level only.** For current partner state, use supply_model.
- **Key Columns**: lco_id_long, status, added_time, city, zone, partner_name, onboarding_date, partner_id
- **CRITICAL**: This is a snapshot table. Each day has a complete copy of all partners. Query a single date: `DATE("added_time") = :target_date`. Querying across multiple dates will multiply counts!
- **Statuses (actual values in DB)**: `ACTIVE`, `TERMINATION`, `CLOSED`, `TEMPORARY SUSPENSION`, `BLACKLISTED`, `TEST`
- **Active filter**: `LOWER("status") = 'active'` (lowercase column name — needs quoting)
- **Case handling**: Partner statuses may vary in case across tables. Always use `LOWER(status) = 'active'` or `ILIKE` for case-insensitive matching.
- **Latest date**: `SELECT MAX(DATE("added_time")) FROM partner_details_log`
- **All column names are lowercase** — must quote: `"status"`, `"added_time"`, `"lco_id_long"`, etc.
- **Reports**: BDM

### supply_model (PUBLIC)
**Source of truth for current partner data.**
- **Key Columns**: PARTNER_ACCOUNT_ID, partner_status, PARTNER_NAME, PARTNER_MOBILE, PARTNER_ONBOARDING_DATE, PARTNER_TENURE_BUCKET
- **Active filter**: `LOWER(partner_status) = 'active'`
- **Case handling**: Partner statuses may vary in case across tables. Always use `LOWER(status) = 'active'` or `ILIKE` for case-insensitive matching.
- **Geography**: ZONE, CITY, CITY_TIER, PINCODE, ADDRESS, SHARD
- **Onboarding**: PARTNER_ONBOARDING_DATE, PARTNER_TENURE_BUCKET, IS_V2_PARTNER, MIGRATED_TO_V2_TIME, ACCOUNT_MANAGER
- **Team Size**: ROHIT_AT_ONBOARDING, ROHIT_CURRENT, NUMBER_OF_ROHITS, PARTNER_SIZE
- **Install Performance**: TOTAL_INSTALL, INSTALL_FIRST_30DAY, INSTALL_RATE_FIRST_30DAY, TOTAL_INSTALL_RATE, INSTALL_RATE_ASSIGNED, INTRESTED, MARKEDINTRESTED_30DAY, ASSIGNED, INSTALL_WITHIN_TAT, INSTALL_WITHIN_TAT_WORKING_HR, INSTALL_WITHIN_PROMISED
- **Ratings**: SERVICE_RATING, AVG_INSTALL_RATING, AVG_CUSTOMER_RATING, DISPLAY_RATING
- **Tickets**: TICKET_CREATED, TICKET_RESOLVED, TICKET_REOPENED, TICKET_RESOLVED_WITHIN_TAT, AVG_RESOLUTION, FONI_TICKET, COMPLAINT_RATIO
- **Revenue**: REVENUE_SHARE_TO_WIOM, REVENUE_TO_PARTNER, INSTALL_INCENTIVE, RATING_INCENTIVE, CURRENT_BALANCE, PARTNER_PROFIT
- **Segmentation**: ROUTER_UTILIZATION_SEGMENT, INSTALL_ACTIVITY_CLASS, RETENTION_CLASS, PARTNER_EARNING_CONSISTENCY, ACTIVE_CUSTOMER_D_1, ACTIVE_CUSTOMER_SEGMENT
- **Join key**: `PARTNER_ACCOUNT_ID = ACCOUNT_ID` in TASK_LOGS
- **Reports**: OKR2, OKR4b

### T_ACCOUNT (PUBLIC)
**Account master table with shard and account type information.**
- **Key Columns**: id (NUMBER — account ID), account_type (VARCHAR — account type identifier)
- **Reports**: BDM, OKR2

### T_ADDRESS (PUBLIC)
**Address/location details for accounts.**
- **Key Columns**: id (NUMBER — address ID), latitude (FLOAT — address latitude), longitude (FLOAT — address longitude), city (VARCHAR — city name), state (VARCHAR — state name)
- **Reports**: OKR4a

### T_WG_CUSTOMER_AUDIT (PUBLIC)
**Audit log for customer-to-device/partner mapping changes. Tracks historical changes to t_wg_customer.**
- **Key Columns**: nasid (NUMBER — NAS ID), device_id (VARCHAR — device ID), account_id (NUMBER — customer account ID), modified_time (TIMESTAMP — modification timestamp)
- **Reports**: OKR4a, BDM

### T_WIOM_LEAD (PUBLIC)
**Lead records for customer acquisition. Tracks leads assigned to partners.**
- **Key Columns**: mobile (VARCHAR — customer mobile), lco_account_id (NUMBER — partner account ID; certain IDs are excluded as test accounts), id (NUMBER — lead ID)
- **Reports**: BDM

### TEST_LCO_ACCOUNT_ID (PUBLIC)
**Reference table of test/internal partner account IDs to exclude from analytics.**
- **Key Columns**: lco_account_id (VARCHAR — test partner account ID to exclude)
- **Common Filters**: Used as exclusion list — `WHERE lco_account_id NOT IN (SELECT lco_account_id FROM TEST_LCO_ACCOUNT_ID)`
- **Reports**: BDM, OKR4b

### CT_PARTNER_APP_LAUNCH (PUBLIC)
**Partner app launch/usage events. Tracks when partners open the Wiom app.**
- **Key Columns**: user_id (VARCHAR — partner account ID), TIMESTAMP (TIMESTAMP — app launch timestamp, UTC), user_role (VARCHAR — user role: 'OWNER', 'ADMIN', etc.)
- **Common Filters**: `user_role IN ('OWNER','ADMIN')` for valid launches
- **Reports**: OKR2

### t_account_mapping1 (PUBLIC, Fivetran)
**Account membership mappings with Wiom member metadata.**
- **Key Columns**: account_id, mapping_type, mapping_params (JSON)
- **Wiom member check**: `json_extract_path_text(mapping_params, 'wiom_member') = 'true'`
- Used for: Membership extension in Active Customers calculation (extends plan expiry by 30 days)

---

## Plan & Payment Tables

### t_plan_configuration (PUBLIC, Fivetran)
**Plan metadata — validity, pricing, speed, plan names.**
- **Key Columns**: id, time_limit (seconds), speed_limit_mbps, plan_code, NAME, ACTIVE, CONCURRENT_DEVICES
- **Plan validity**: `ROUND(time_limit/60/60/24)` gives days
- **M+ plans**: >= 28 days (NSM) or >= 26 days (OKR1)
- **PayG/STP plans**: < 28 days (NSM) or < 26 days (OKR1)
- **Price extraction**: `REGEXP_SUBSTR(NAME::STRING, '[\u20b9_][[:space:]]*([0-9]+)', 1, 1, 'e', 1)`

### payment_logs (PUBLIC)
**Payment gateway event logs.**
- **Success filter**: `mobile>'5999999999' AND event_name='order_succeeded'`
- **Transaction ID from JSON**: `PARSE_JSON(data):"transaction_id"::STRING`

### mobile_recharge_logs (PUBLIC)
**VAS (Value-Added Services) mobile recharge events via PayU.**
- **Success filter**: `event_name='payu_recharge_api' AND TO_VARCHAR(TRY_PARSE_JSON(data):status) ILIKE '%SUCCESS%' AND TO_VARCHAR(TRY_PARSE_JSON(data):paidAmount) <> ''`
- **IST date**: `CAST(DATEADD(MINUTE,330,added_time) AS DATE)`

---

## Service & Quality Tables

### service_ticket_model (PUBLIC)
**Support tickets with SLA tracking, resolution status, customer/partner mapping.**
- **Key Columns**: ticket_id, kapture_ticket_id, ticket_type_final, cx_px, last_title, ticket_added_time, final_resolved_time, resolution_tat_bucket, CURRENT_partner_account_id, device_id
- **Non-shifting**: `LOWER(last_title) NOT ILIKE '%shifting%'`
- **Exclude CC**: `LOWER(cx_px) <> 'cc'`
- **Cx only**: `cx_px = 'Cx'`; **Px only**: `cx_px = 'Px'`
- **SLA targets**: type 3 = 4hr working (11AM-9PM IST), type 1 = 21d, type 2 = 3d, type 4 = 1d
- **Within TAT**: `resolution_tat_bucket = 'within TAT'`
- **RDNI tickets**: `LAST_TITLE ILIKE '%Internet Issues|Recharge done but internet not working%'`
- **FONI tickets**: "Fiber or No Internet" — critical connectivity complaints
- **Reports**: OKR1, OKR2, OKR4a, OKR4b

### AMEYO_CALL_DETAILS_REPORT (PUBLIC)
**Primary source for CX calling data. Records all inbound customer calls end-to-end — from IVR entry through agent handling. Every call that enters the Wiom IVR system gets a record here.**
- **Key Columns**: CALL_ID (TEXT — Ameyo internal ID), CRT_OBJECT_ID (TEXT — maps to CUSTOMER_INBOUND_CALL_LOG.CALL_ID for cross-referencing), CALL_TIME (TEXT — format `DD/MM/YYYY H:MI:SS AM/PM`, single-digit hour possible — use `TRY_TO_TIMESTAMP` or `CAST(CALL_TIME AS TIMESTAMP)`), PHONE (TEXT — customer number), DID (TEXT — Wiom number called), QUEUE_NAME (TEXT — agent queue routed to, NULL if IVR-only), SYSTEM_DISPOSITION (TEXT — call outcome), IVR_TIME (TEXT — time spent in IVR as HH:MI:SS), CUSTOMER_TALK_TIME (TEXT — agent talk time as HH:MI:SS), CUSTOMER_HOLD_DURATION (TEXT — hold time as HH:MI:SS), ACW_DURATION (TEXT — after-call work as HH:MI:SS), USER_NAME (TEXT — agent name), CALL_TYPE (TEXT — call direction)
- **All columns are TEXT** — cast durations to TIME for calculations: `DATEDIFF('second', '00:00:00'::TIME, CUSTOMER_TALK_TIME::TIME)`
- **Date parsing**: `TRY_TO_DATE(SUBSTRING(CALL_TIME, 1, 10), 'DD/MM/YYYY')` — use TRY_TO_* to handle single-digit hours
- **Header row filter**: Always add `WHERE CALL_TIME <> 'CALL_TIME'` — table has a header row stored as data
- **SYSTEM_DISPOSITION values**: CONNECTED (agent answered), CALL_HANGUP (customer abandoned — in IVR or agent queue), NO_ANSWER (no answer from system), CALL_NOT_PICKED (agent didn't pick), CALL_DROP (call dropped), ATTEMPT_FAILED, PROVIDER_TEMP_FAILURE, PROVIDER_FAILURE, FAILED, BUSY
- **QUEUE_NAME values (CX service)**: `high_pain_queue` (high severity — open ticket past SLA, repeat callers), `low_pain_queue` (standard service), `payG_Queue` (PayG customers). NULL = call handled entirely in IVR, never routed to agent queue
- **QUEUE_NAME values (other)**: `sales_queue`, `booking_queue`, `PartnerSupportQueue` (partner calls — but prefer partner_call_log table for partner analysis)
- **CALL_TYPE values**: `inbound.call.dial` (customer inbound), `outbound.manual.dial` (agent outbound), `transferred.to.campaign.dial` (transferred), `outbound.auto.dial` (auto-dialer)
- **CX service queues filter**: `QUEUE_NAME IN ('high_pain_queue', 'low_pain_queue', 'payG_Queue')` — confirmed by Sajal Jain
- **Missed/abandoned rate**: `SYSTEM_DISPOSITION = 'CALL_HANGUP'` is the primary "missed" metric — customer hung up either during IVR or while waiting for agent. For agent-level miss rate, filter to non-NULL QUEUE_NAME first
- **Data range**: Jan 26, 2026 onwards (post-PayG launch)
- **Refresh**: Daily sync, data available through previous day
- **Cross-reference**: `CRT_OBJECT_ID = CUSTOMER_INBOUND_CALL_LOG.CALL_ID` for IVR routing details (LAST_STAGE, AGENT info)
- **Reports**: CX call volume, service level, abandonment rate

### CUSTOMER_INBOUND_CALL_LOG (PROD_DB.POSTGRES_RDS_PARTNER_CALL_LOG_IVR)
**IVR routing layer for customer inbound calls. Shows IVR decision tree, agent assignment, and ticket linkage. Cross-reference with AMEYO for complete picture.**
- **Key Columns**: CALL_ID (VARCHAR — links to AMEYO.CRT_OBJECT_ID), FROM_NUMBER (VARCHAR — customer number), CALL_STATUS (VARCHAR — CONNECTED, MISSED, RINGING, ERROR), QUEUE (VARCHAR — IVR flow ID, maps to IVR_FLOW_TABLE.FLOW_ID), START_STAGE (VARCHAR — entry point, typically INSTALLATION_COMPLETED), CALL_FLOW_STAGE (VARCHAR — comma-separated full IVR decision path), LAST_STAGE (VARCHAR — final IVR decision node), AGENT (VARIANT — JSON with `id` and `name`, NULL id = IVR-only), TICKET (VARIANT — linked ticket info), CALL_FLOW_DECISION_DATA (VARIANT — JSON with customerBooking, deviceId, installationDate etc.), CREATED_AT (TIMESTAMP — already IST), RECORDING_URL (VARCHAR)
- **CALL_STATUS caveat**: CONNECTED means IVR connected to the call, NOT that an agent answered. Use `TRY_PARSE_JSON(AGENT):id::STRING IS NOT NULL` to check if call reached an agent
- **LAST_STAGE values (service)**: PING_ACTIVE (plan+ping active, no real issue), NO_OPEN_TICKET (new complaint, routed to agent), OUTAGE (outage detected), IVR_TICKET (has open ticket, IVR status update), OPEN_TICKET_EXCEEDS_THRESHOLD_TIME (high pain, ticket past SLA), HIGH_CALL_VOLUME_SAME_DAY (repeat caller), PLAN_INACTIVE (expired plan), CALL_BEFORE/AFTER_TICKET_FOLLOW_UP_DURATION, PARTNER_BLOCKED, HIGH_CALL_VOLUME_LOOKBACK_PERIOD, CALL_WITHIN_INSTALLATION_GRACE_PERIOD
- **_FIVETRAN_DELETED**: All NULL in this table — do NOT filter on it
- **Data range**: Jan 21, 2026 onwards
- **Reports**: IVR routing analysis, call classification

### IVR_FLOW_TABLE (PUBLIC)
**IVR flow/queue mapping table. Maps queue IDs to flow names and categories.**
- **Key Columns**: USED_FOR (VARCHAR — master flow/queue name: Service, Booking, Sales, Wiom Net, PayG), FLOW_NAME (VARCHAR — L2 flow name within the master queue), FLOW_ID (NUMBER — queue/flow ID; joins to CUSTOMER_INBOUND_CALL_LOG.QUEUE via TRY_TO_NUMBER)
- **Service queue**: FLOW_ID 1-20 (USED_FOR = 'Service')
- **Booking queue**: FLOW_ID 21-35, 42 (USED_FOR = 'Booking')
- **Other**: Sales (36), Wiom Net (37-38), PayG (39-42)
- **Reports**: IVR/CX analysis

### SLA_BREAKDOWN_V2 (PUBLIC)
**Partner-level installation performance metrics (strike rate, catch rate) by date.**
- **Key Columns**: partner_id (VARCHAR — partner account ID), strike_rate (FLOAT — partner installation strike rate), catch_rate (FLOAT — partner catch rate), date (DATE — metric date)
- **Reports**: OKR2

### RATING (DYNAMODB)
**Customer ratings for tickets and installation tasks.**
- **Key Columns**: created (VARCHAR — rating creation timestamp), ratable_entity (VARCHAR — 'ticket' or 'task'), rating (NUMBER — rating score 1-5)
- **Reports**: OKR2

### RENEWALS_MODEL (PUBLIC)
**Pre-built model tracking recharge-to-recharge cycles and churn. Each row represents a recharge event with forward-looking next recharge info.**
- **Key Columns**: router_nas_id (VARCHAR — NAS ID), recharge_date (DATE — current recharge date), next_recharge_date (DATE — next recharge date; NULL = churned), plan_expiry (DATE — plan expiry date)
- **Reports**: BDM

### PARTNER_INFLUX_SUMMARY (PUBLIC)
**Partner uptime/ping summary for QOS calculation.**
- **Key Columns**: partner_id, TOTAL_PINGS_RECEIVED, TOTAL_EXPECTED_PINGS, appended_date
- **Actual date**: `DATEADD(day,-1,appended_date)`
- **Uptime**: `TOTAL_PINGS_RECEIVED / TOTAL_EXPECTED_PINGS`
- **Reports**: OKR4b

### tata_ivr_events (PUBLIC)
**IVR call events from Tata.**
- **Inbound filter**: `direction = 'inbound'`
- **Missed filter**: `status = 'missed'`
- **Reports**: OKR4b

### USER_CONNECTION_CALL_LOGS
**Schema**: `PROD_DB.POSTGRES_RDS_PARTNER_CALL_LOG_IVR`
**Call logs for partner-to-customer calls routed through Exotel during booking→install flow.**
- **Key Columns**: CALL_ID, FROM_NUMBER, TO_NUMBER, RECORDING_URL, CALL_STATUS, CALL_DURATION, DISCONNECTED_BY, CREATED_AT (IST — no UTC conversion needed)
- **Call statuses**: CONNECTED, MISSED_CALL, CANCELLED, REJECTED, UNKNOWN
- **Phone number normalization**: Always use `RIGHT(from_number, 10)` before joining
- **Recording URL cleanup**: `CASE WHEN recording_url IS NULL OR TRIM(recording_url) IN ('', 'null') THEN NULL ELSE recording_url END`
- **Join to customer**: Match `RIGHT(from_number, 10)` or `RIGHT(to_number, 10)` to `TASK_LOGS.MOBILE`
- **Scope**: Booking→install flow only. Does not cover service tickets or recovery calls.
- **Call window**: Scope between ASSIGNED event time and OTP_VERIFIED event time for a given customer

### TASKS (DYNAMODB_READ)
**Router pickup (PUT) ticket records.**
- **Key Columns**: TICKET_ID, NAS_ID, CX_MOBILE, STATUS (0=Unassigned, 1=Assigned, 2=Resolved, 3=Unresolved), TICKET_STATUS, TYPE, CREATED (ticket creation timestamp, already IST), DUE_AT (already IST)
- **PUT ticket filter**: `type = 'ROUTER_PICKUP'`
- **Ticket creation paths**: System-created (at R15 = 15 days post plan expiry) or Self-created (customer initiates R0→R15)
- **Resolution outcomes**: `ROUTER_RECOVERED` (device retrieved), `customer_recharged` (customer paid), `bug` (data issue)
- **Status 3 sub-cases**: `DATEDIFF(day, TICKET_CREATED_AT, TASK_RESOLVED_TIME) = 21` → no action/auto-closed; `< 21` → action taken but failed
- **Self-drop**: `SELF_DROP = TRUE` (customer drops at partner office), `FALSE` (partner picks up from home)

### TASK_PERFORMANCE
**Ticket resolution timing for PUT tickets.**
- **Key Columns**: TASK_RESOLVED_TIME (already IST — no UTC conversion needed)
- **Used for**: Calculating resolution TAT for router recovery tickets

### SECURITY_DEPOSIT_ORDERS
**Schema**: `PROD_DB.CUSTOMER_DB_CUSTOMER_PROFILE_SERVICE_PUBLIC`
**Audit/log table for security deposit refund status. One customer can have multiple rows.**
- **Key Columns**: UPI_ID, SECURITY_DEPOSIT_AMOUNT, PICKUP_CHARGE, LATE_FEE, TOTAL_CHARGES, FINAL_ORDER_AMOUNT, PAYMENT_STATUS, RETURN_DATE, CREATED_AT (UTC), UPDATED_AT (UTC), COMPLETED_AT, FAILURE_REASON, PARTNER_ADDRESS
- **Payment statuses**: CREATED → PROCESSING (hit Razorpay) → SUCCESSFUL (refund sent to UPI) | CLOSED (customer recharged)
- **Security deposit**: Only for PayG customers (install >= 2026-01-26); zero for nPayG
- **Late fee**: Charged if no action taken R15 to R19 (R15 + 5 days)
- **Pickup charge**: Charged when SELF_DROP = FALSE
- **Final amount**: `SECURITY_DEPOSIT_AMOUNT - TOTAL_CHARGES`
- **Join to tickets**: Window-based join scoped between TICKET_CREATED_AT and NEXT_TICKET_CREATED_AT
- **Timezone**: CREATED_AT and UPDATED_AT are UTC — apply +330 min before comparing with IST ticket timestamps

### CUSTOMER_LOGS (PUBLIC)
**Customer lifecycle events.**
- **Key Columns**: mobile, event_name, added_time (UTC)
- **Renewal filter**: `event_name = 'renewal_fee_captured'`
- **Used for**: Finding last recharge event in router recovery flow

### incidents (BUSINESS_EFFICIENCY_ROUTER_OUTAGE_DETECTION_PUBLIC)
**Master table of all detected router outage incidents. Each incident is raised automatically when one or more routers under a partner go offline.**
- **Full path**: `PROD_DB.BUSINESS_EFFICIENCY_ROUTER_OUTAGE_DETECTION_PUBLIC.incidents`
- **Grain**: 1 row = 1 outage incident
- **Refresh**: Near real-time via Fivetran
- **Key Columns**: ID (PK, incident ID), PARTNER_ID (BIGINT), SEVERITY (VARCHAR — MICRO/LOCAL/MAJOR), INITIAL_SEVERITY (VARCHAR — at first detection), DEVICE_COUNT (INTEGER — total devices impacted), INCIDENT_OPEN_DEVICE_COUNT (still down), RECOVERED_DEVICE_COUNT, RECOVERY_PERCENTAGE (FLOAT 0-1), STATUS (ACTIVE/CLOSED), IS_CLOSED (BOOLEAN), DURATION_MINUTES (INTEGER), FIRST_FAIL_TIMESTAMP (when first device failed), CREATED_AT (incident record created — ~20 min after first fail), CLOSED_AT (nullable — null for ACTIVE), SIZE_BUCKET (TINY/SMALL/MEDIUM/LARGE), DURATION_BUCKET (SHORT/MEDIUM/LONG)
- **Fivetran filter**: ALWAYS filter `_FIVETRAN_DELETED = false` — deleted records appear on still-active incidents
- **Severity rules**: MICRO (1 device), LOCAL (2-5 devices), MAJOR (6+ devices). Can escalate from INITIAL_SEVERITY.
- **Zombie incidents**: DURATION_MINUTES > 10080 (7 days) likely stale/never-closed — flag these
- **Detection lag**: CREATED_AT - FIRST_FAIL_TIMESTAMP is consistently ~20 minutes
- **Join to devices**: `ID = incident_impacted_device.INCIDENT_ID`
- **Join to partner**: `PARTNER_ID` to partner master / HIERARCHY_BASE
- **Reports**: OKR4b

### incident_impacted_device (BUSINESS_EFFICIENCY_ROUTER_OUTAGE_DETECTION_PUBLIC)
**Bridge table linking each outage incident to specific router devices affected. Tracks per-device recovery.**
- **Full path**: `PROD_DB.BUSINESS_EFFICIENCY_ROUTER_OUTAGE_DETECTION_PUBLIC.incident_impacted_device`
- **Grain**: 1 row = 1 device x 1 incident
- **Key Columns**: ID (PK), INCIDENT_ID (FK to incidents.ID), DEVICE_ID (VARCHAR — GX/SY prefix), STATUS (RECOVERED/PENDING), RECOVERY_AT (TIMESTAMP — null for PENDING devices), CREATED_AT (when device was added to incident), UPDATED_AT
- **Fivetran filter**: ALWAYS `_FIVETRAN_DELETED = false`
- **Recovery**: STATUS='RECOVERED' has non-null RECOVERY_AT; STATUS='PENDING' has null RECOVERY_AT
- **Bulk recovery**: Many devices recovering at same timestamp indicates upstream fix (NAS restart, ISP restore)
- **Dedup**: (INCIDENT_ID, DEVICE_ID) should be unique
- **Fivetran sync lag**: ~13 minutes from source to Snowflake
- **Join to incidents**: `INCIDENT_ID = incidents.ID` for severity, partner, duration
- **Join to ping data**: `DEVICE_ID = HOURLY_DEVICE_PING_INFLUX.DEVICE_ID`
- **Reports**: OKR4b

### IMPACTED_DEVICES / PARTNER_OUTAGE_ALERTS (Legacy)
**Schema**: `PROD_DB.BUSINESS_EFFICIENCY_ROUTER_OUTAGE_DETECTION_PUBLIC`
- **Note**: Prefer `incidents` + `incident_impacted_device` tables above for current analysis. These legacy tables may still be referenced in older reports.
- **Key Columns (IMPACTED_DEVICES)**: device_id, partner_id, alert_id, window_datetime, recovery_timestamp
- **Key Columns (PARTNER_OUTAGE_ALERTS)**: ID, outage_start_timestamp, ALERT_STATUS
- **Active/resolved filter**: `alert_status IN ('ACTIVE','RESOLVED')`
- **Reports**: OKR4b

---

## Device Telemetry & Network Tables

### HOURLY_DEVICE_PING_INFLUX (PUBLIC)
**Structured, processed hourly router ping data from InfluxDB. Primary table for device uptime, outage detection, and fiber signal quality analysis.**
- **Grain**: 1 row = 1 router device x 1 hour
- **Refresh**: Hourly
- **Key Columns**:
  - **Identity**: PARTNER_ID (BIGINT), DEVICE_ID (VARCHAR — GX/SY prefix), NAS_ID (BIGINT)
  - **Time**: DATE_IST (date), HOUR_START_IST, HOUR_END_IST (always 59m59s after start)
  - **Ping data**: TOTAL_PINGS_RECEIVED (0-12 per hour, 5-min intervals), TOTAL_PINGS_MISSED, PING_BITMAP (12-char binary — '1'=received, '0'=missed per 5-min slot)
  - **Outage detail**: FRAGMENTED_PING_MISSES (isolated single misses), CONTINUOUS_MISSED_PING_INSTANCES (consecutive miss streaks), MAX_PINGS_MISSED_IN_CONTINUOUS_INSTANCE, MIN_PINGS_MISSED_IN_CONTINUOUS_INSTANCE
  - **Outage timing**: FIRST_MISS_TIMESTAMP_IST, LAST_MISS_TIMESTAMP_IST, FIRST_PING_TS_IST, LAST_PING_TS_IST
  - **Fiber signal**: OPTICAL_MIN, OPTICAL_AVG, OPTICAL_MAX (dBm). Acceptable: -8 to -24. Weak: below -25. Critical: below -27
  - **WiFi clients**: CONNECTED_2G_MAX, CONNECTED_5G_MAX, CONNECTED_WIOMNET_MAX
  - **Other**: BANDSTEERING_FLAG (1=enabled, 0=disabled), SSID_JSON, SOURCE_TABLE (='T1'), UPDATED_AT, INSERTED_AT
- **Timestamps are already IST** — no UTC conversion needed
- **Uptime formula**: `(TOTAL_PINGS_RECEIVED / 12.0) * 100` = hourly uptime %
- **Outage duration**: `TOTAL_PINGS_MISSED * 5` = minutes offline in the hour
- **RECEIVED + MISSED should equal 12** (12 five-minute check slots per hour)
- **Dedup key**: (DEVICE_ID, DATE_IST, HOUR_START_IST) should be unique
- **Join to usage**: `NAS_ID = HOURLY_USAGE_PRORATED_DT.NASID` + `HOUR_START_IST = HOUR_START`
- **Join to incidents**: `DEVICE_ID = incident_impacted_device.DEVICE_ID`
- **Join to customer**: via DEVICE_ID to t_wg_customer.DEVICE_ID
- **Join to partner**: PARTNER_ID to HIERARCHY_BASE
- **Reports**: OKR4b, Product

### router_logs (PUBLIC)
**Router event logs including speed tests, sessions, power events.**
- **Key Columns**: KEY (= device_id), EVENT_NAME, ADDED_TIME, DATA (VARIANT/JSON), MOBILE
- **Speed test filter**: `EVENT_NAME = 'speed_test_result'` — speed in `PARSE_JSON(DATA):speed::STRING` (Mbps)
- **Other events**: `session_started`, `session_ended`, `power_up`, `power_down`, `speed_test_result_v2`, `speed_test_result_v3`
- **Join to device**: `KEY = device_id`
- **IST date**: `TO_DATE(DATEADD(minute,330,ADDED_TIME))`
- **Reports**: OKR4b

### HOURLY_DEVICE_PING_HEALTH_VW (PUBLIC)
**Hourly device ping health view — similar to HOURLY_DEVICE_PING_INFLUX with additional optical signal columns.**
**Note**: Prefer HOURLY_DEVICE_PING_INFLUX for most analysis. Use this view only when optical signal columns are specifically needed.
- **Key Columns**: NAS_ID (long), HOUR_START_IST, DATE_IST, TOTAL_PINGS_RECEIVED, FIRST_PING_TS_IST, CONNECTED_2G_MAX, CONNECTED_5G_MAX, CONNECTED_WIOMNET_MAX
- **Pings**: 0-12 per hour (12 five-minute checks). 0 = no internet that hour.
- **Timestamps are already IST** — no UTC conversion needed
- **Join to TRUM**: via `router_nas_id` = NAS_ID

### HOURLY_USAGE_PRORATED_DT (PUBLIC)
**Hourly data usage per router.**
- **Key Columns**: NASID (long NAS ID), HOUR_START (UTC — add 330 min for IST), TOTAL_BYTES_HOURLY
- **Convert to GB**: `TOTAL_BYTES_HOURLY / (1024.0 * 1024.0 * 1024.0)`

### BANDSTEERING_DAILY (PUBLIC)
**Daily band steering snapshot — limited historical data (Feb 2026 only).**
- **Key Columns**: DEVICEID, LCOACCOUNTID, NASID, CAPTURED_DATE, BAND_STEERING_FLAG
- **Note**: Only has data for Feb 6-16, 2026 (~1,036 devices). Likely a one-off analysis table. Prefer HOURLY_DEVICE_PING_INFLUX for current band steering data.

### WIOM_DEVICES_LOCATION (PUBLIC)
**Physical location of deployed Wiom devices (routers). Tracks lat/long and last activity.**
- **Key Columns**: device_id (VARCHAR — physical device ID), latitude (FLOAT — device latitude), longitude (FLOAT — device longitude), last_seen (TIMESTAMP — last seen timestamp)
- **Reports**: OKR4a, Supply

### GINIE_LOGS (PUBLIC)
**Serviceability check logs from the Ginie engine. Records partner distance calculations for leads.**
- **Key Columns**: mobile (VARCHAR — customer mobile), EVENT_NAME (VARCHAR — 'returned_response' for serviceability results), added_time (TIMESTAMP — event timestamp), data (VARIANT — JSON with partners_dis array containing partner distances)
- **Reports**: Product

### T_SERVICEABILITY_LOGS (PROD_DB.MYSQL_GENIE1)
**Raw serviceability check logs from the Genie microservice. Contains request/response payloads.**
- **Key Columns**: mobile (VARCHAR — customer mobile, extracted from JSON request), created_at (TIMESTAMP — log timestamp), request (VARIANT — JSON request payload with lead phone number), response (VARIANT — JSON response with nearest_within_radius distance)
- **Reports**: Product

### T_INVENTORY_REQUEST (PUBLIC)
**Router/device inventory requests from partners. Tracks request lifecycle from creation to delivery.**
- **Key Columns**: id (NUMBER — request ID), account_id (NUMBER — partner account ID), request_type (VARCHAR — type of inventory request), status (VARCHAR — pending, approved, rejected, dispatched, delivered), created_on (TIMESTAMP — request creation time, UTC), quantity (NUMBER — number of devices requested)
- **Reports**: Supply

### t_controller (PUBLIC, Fivetran)
**Router/NAS controller information including ISP details, firmware, SSID config.**
- **Key Columns**: ROUTER_NAS_ID, CONFIGS, SSIDDATA (JSON array of SSIDs with radio info), DEVICE_TYPE, VERSION, FIRMWAREVERSION, GATEWAYINFO (JSON with ISP as `as_name`), SHARD
- **ISP extraction**: `PARSE_JSON(GATEWAYINFO):as_name::STRING`
- **SSID config**: `SSIDDATA` is a JSON array with objects containing `ssid`, `password`, `mode`, `radio` (radio0=2.4G, radio1=5G)
- **Reports**: OKR4b

---

## Reference & Audit Tables

### CALENDAR (PUBLIC)
**Date dimension table with sprint metadata.**
- **Key Columns**: DATE, day_of_sprint, sprint_number, sprint_start, sprint, DAY_NAME, MONTH_NO, YEAR
- **Sprint**: 15-day cycles (1st-15th, 16th-EOM)
- **Current sprint**: sprint_number = 0; Previous: sprint_number = 1
- **Join**: `metric_table.dt = DATE(calendar."DATE")`
- **Reports**: ALL

### BOOKING (DYNAMODB / DYNAMODB_READ)
**Booking lifecycle records. Tracks payments, refunds, rebookings.**
- **Key Columns**: mobile, nasid, booking_payment, installation_payment, refund_initiated, booking_fee, cancellation_booking_date, added_time, modified_time
- **Reports**: BDM

### profile_lead_model (PUBLIC)
**Installation source tracking. Tracks lead origin and installation time.**
- **Key Columns**: MOBILE, BREAK_KEY, JOURNEY_START, JOURNEY_END, CUSTOMER_ACCOUNT_ID, CITY, lead_first_booking_conf_time, lead_installation_time, source_acc_booking_conf, bonus_conf_lead
- **Reports**: OKR1

### data_usage_okr (PUBLIC)
**Pre-aggregated daily data usage per NAS ID.**
- **Key Columns**: nasid, dt, total_data_used (GB)
- **Reports**: OKR1

### t_device_audit (PUBLIC, Fivetran)
**Device lifecycle events / audit trail.**
- **Key Columns**: device_id, user_account_id, modified_time, lco_account_id, nas_id
- Used for: Device recovery/redeployment tracking (check if user_account_id changed)
- **Reports**: OKR4a

### t_account_balance_sheet1 (PUBLIC)
**Partner financial data / wallet balance sheet.**
- **Key Columns**: transaction_id, account_id, balance, action, remark, added_time, extra_data
- **Commission**: `action = 'COMMISSION_ADDED'`
- **Withdrawal**: `action = 'AMOUNT_WITHDRAWN'`
- **Reports**: OKR2

### BDO_COST / BDO_INFO / CC_COST (PUBLIC)
**Cost tables for finance.**
- BDO_COST: BDO cost allocation per cluster per month
- BDO_INFO: BDO daily activity log with mandays per city
- CC_COST: Call center cost per day

### ISSUE (JIRA)
**JIRA issue tracking.**
- **Schema**: `prod_db.jira`
- **Bugs filter**: `issue_type='10027'`
- **Resolved**: `status_category=3`
- **Reports**: OKR4b

### DAILY_USAGE_L1_DT (PUBLIC)
**Daily data usage per customer per connection type. Granular usage table with session-level detail.**
- **Key Columns**: DATE_IST (DATE — date in IST), NASID (VARCHAR — long router NAS ID), CONNECTION_TYPE (VARCHAR — primary or wiomnet/secondary), MOBILE (VARCHAR — customer mobile), ACTIVE_HOURS_COUNT_DAILY (NUMBER — hours customer was active), TOTAL_DOWNLOAD_BYTES_DAILY (FLOAT — total bytes downloaded), TOTAL_UPLOAD_BYTES_DAILY (FLOAT — total bytes uploaded), TOTAL_DATA_BYTES_DAILY (FLOAT — total bytes up+down), FIRST_SESSION_TS_DAILY (TIMESTAMP — first session timestamp), LAST_SESSION_TS_DAILY (TIMESTAMP — last session timestamp)
- **Reports**: (Usage/Product analysis)

### partner_call_log (PROD_DB.POSTGRES_RDS_PARTNER_CALL_LOG_IVR)
**PTL (Partner Trust Line) call logs. Inbound calls from partners to Wiom's partner support line. This is the primary source for partner calling data.**
- **Also known as**: PTL calls, partner calls, partner support calls, Partner Trust Line
- **Key Columns**: CALL_ID (VARCHAR — unique call identifier), FROM_NUMBER (VARCHAR — calling number of the partner), DISPOSITION (VARIANT — JSON array with key "bucket" for call type), CREATED_AT (TIMESTAMP — timestamp of the call, already IST), CALL_META (VARIANT — JSON array with key "callStatus" for status: RINGING, MISSED, CONNECTED), CALL_STATUS (VARCHAR — e.g., NO_DISPOSITION_REQUIRED, COMPLETED), _FIVETRAN_DELETED (BOOLEAN — NULL in this table, do NOT filter on it)
- **Note**: AMEYO also has partner calls in `QUEUE_NAME = 'PartnerSupportQueue'`, but this table is the primary source for partner/PTL call analysis
- **Reports**: PTL call volume, partner support analysis

### FACEBOOK_ADS (FACEBOOK_ADS schema / PUBLIC)
**Ad spend and impressions.**
- After 2025-09-21: `PROD_DB.FACEBOOK_ADS.CUSTOM_REPORT_2`
- Before 2025-09-21: `prod_db.public.facebook_ads`
- Join `fb_ads_mapping` on adset_name for city/campaign_type
- Exclude experiment and partner campaigns

---

## Product Context & Jira Tables

### DATE_CONTEXT_EVENTS (PUBLIC)
**Product release/change log for RCA and analysis context. Tracks what changed, when, and why across all apps.**
- **Grain**: 1 row = 1 product change/release event
- **Key Columns**: CONTEXT_ID (NUMBER, autoincrement PK), DT (VARCHAR DD-MM-YYYY — date of change), CONTEXT_CATEGORY (VARCHAR — RELEASE, DATA_CHANGE, DECISION, OPERATIONAL_CHANGE), CONTEXT_SUBCATEGORY (VARCHAR — APP_RELEASE, BACKEND_RELEASE, INTERNAL_TOOL_CHANGE, FEATURE_FLAG_CHANGE, DATA_BUG_FIX, FEATURE_HALT, OPERATIONAL_CHANGE, CONFIG_CHANGE, SERVICE_CHANGE, INCENTIVE_POLICY_CHANGE), PRODUCT_AREA (VARCHAR — Partner App Updates, Customer App Updates, Wiom Hub Updates, IX Infrastructure, etc.), IMPACTED_PERSONAS (VARCHAR — Customer, Partner, Rohit, Internal, Internal-CX, Multiple), TITLE (VARCHAR — short title), JTBD (VARCHAR — job-to-be-done / why this change matters), DETAILS (VARCHAR — specifics of what changed), JIRA_KEYS (VARCHAR — comma-separated Jira keys if available), SOURCE_REF (VARCHAR — where info came from), CREATED_AT (VARCHAR — auto-set timestamp)
- **Date column is text**: Always use `TRY_TO_DATE(DT, 'DD-MM-YYYY')` for date comparisons and sorting
- **Coverage**: Nov 2025 onwards. 82 entries as of Mar 24, 2026.
- **Use for**: Understanding what product changes were live on a given date when doing RCA. Join by date range to any metric to identify potential causes of anomalies.
- **Example query**: Find all changes in a date range:
  ```sql
  SELECT * FROM PROD_DB.PUBLIC.DATE_CONTEXT_EVENTS
  WHERE TRY_TO_DATE(DT, 'DD-MM-YYYY') BETWEEN '2026-02-01' AND '2026-02-28'
  ORDER BY TRY_TO_DATE(DT, 'DD-MM-YYYY');
  ```
- **Example RCA pattern**: When investigating a metric anomaly, pull context events around the date:
  ```sql
  SELECT DT, CONTEXT_CATEGORY, PRODUCT_AREA, TITLE, DETAILS
  FROM PROD_DB.PUBLIC.DATE_CONTEXT_EVENTS
  WHERE TRY_TO_DATE(DT, 'DD-MM-YYYY') BETWEEN DATEADD(day, -3, :anomaly_date) AND DATEADD(day, 1, :anomaly_date)
  ORDER BY TRY_TO_DATE(DT, 'DD-MM-YYYY');
  ```
- **Reports**: RCA, Analysis context

### JIRA_ISSUES (CUSTOM_JIRA_API)
**Jira issue tracker data synced via Fivetran. Use PARTNER and CX projects for product change context.**
- **Full path**: `PROD_DB.CUSTOM_JIRA_API.JIRA_ISSUES`
- **Grain**: 1 row = 1 Jira issue
- **Refresh**: Fivetran sync (near real-time)
- **Key Columns**: ISSUE_KEY (VARCHAR — e.g., PARTNER-5278, CX-1030), SUMMARY (VARCHAR — issue title), PROJECT_KEY (VARCHAR — PARTNER, CX, PRD, TPS), PROJECT_NAME (VARCHAR), ISSUE_TYPE (VARCHAR — Story, Bug, Epic, Task, Sub-task), STATUS (VARCHAR — Released, Validation Done, UAT Passed, With Product, In dev, ToDo, etc.), CREATED (TIMESTAMP_TZ — issue creation), UPDATED (TIMESTAMP_TZ — last status change), RESOLUTION_DATE (TIMESTAMP_TZ), ASSIGNEE (VARCHAR), REPORTER (VARCHAR), LABELS (VARCHAR — comma-separated), PRIORITY (VARCHAR), DESCRIPTION (VARCHAR — full issue description), PARENT_KEY (VARCHAR — parent epic/story key)
- **Relevant projects**: PARTNER (WIOM PARTNER) and CX (Customer Tech) — use these for product change context. PRD (Production_Support) and TPS (Test_Production_Support) are bug/support tracking.
- **Released issues**: `STATUS = 'Released'` — these are deployed to production
- **Fivetran columns**: `_FIVETRAN_SYNCED` (sync timestamp), `_FIVETRAN_DELETED` (boolean — filter `= false`)
- **Cross-reference with DATE_CONTEXT_EVENTS**: Match `JIRA_KEYS` column in DATE_CONTEXT_EVENTS to `ISSUE_KEY` here for full Jira details on a context event
- **Example**: Find all released Partner stories in a sprint:
  ```sql
  SELECT ISSUE_KEY, SUMMARY, UPDATED::DATE AS RELEASE_DATE, LABELS
  FROM PROD_DB.CUSTOM_JIRA_API.JIRA_ISSUES
  WHERE PROJECT_KEY IN ('PARTNER', 'CX')
    AND STATUS = 'Released'
    AND UPDATED::DATE BETWEEN '2026-03-01' AND '2026-03-15'
  ORDER BY UPDATED;
  ```
- **Reports**: RCA, Product context
